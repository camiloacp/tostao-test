import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class DemandForecaster:
    """
    Modelo de pronóstico de demanda con intervalos de confianza
    """
    def __init__(self):
        self.models = {}
        self.scalers = {}
        
    def prepare_features(self, df_ventas):
        """Prepara features para el modelo"""
        df = df_ventas.copy()
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Features temporales
        df['dia_semana'] = df['fecha'].dt.dayofweek
        df['mes'] = df['fecha'].dt.month
        df['semana_año'] = df['fecha'].dt.isocalendar().week
        
        # Agregar por semana
        df['año_semana'] = df['fecha'].dt.strftime('%Y-W%U')
        
        # Agregar ventas semanales
        df_semanal = df.groupby(['año_semana', 'id_tienda', 'id_producto']).agg({
            'unidades_vendidas': 'sum'
        }).reset_index()
        
        # Features de tendencia y estadísticas
        features_list = []
        for (tienda, producto), group in df_semanal.groupby(['id_tienda', 'id_producto']):
            group = group.sort_values('año_semana')
            group['ventas_lag1'] = group['unidades_vendidas'].shift(1)
            group['ventas_lag2'] = group['unidades_vendidas'].shift(2)
            group['media_movil_4'] = group['unidades_vendidas'].rolling(window=4, min_periods=1).mean()
            group['std_movil_4'] = group['unidades_vendidas'].rolling(window=4, min_periods=1).std()
            group['tendencia'] = np.arange(len(group))
            features_list.append(group)
        
        df_features = pd.concat(features_list, ignore_index=True)
        df_features = df_features.fillna(0)
        
        return df_features
    
    def train(self, df_ventas):
        """Entrena modelos por SKU-Tienda"""
        df_features = self.prepare_features(df_ventas)
        
        feature_cols = ['ventas_lag1', 'ventas_lag2', 'media_movil_4', 
                        'std_movil_4', 'tendencia']
        
        for (tienda, producto), group in df_features.groupby(['id_tienda', 'id_producto']):
            key = f"{tienda}_{producto}"
            
            # Preparar datos
            X = group[feature_cols].values
            y = group['unidades_vendidas'].values
            
            if len(X) < 5:  # Muy pocos datos
                continue
            
            # Escalar
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Entrenar modelo
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_scaled, y)
            
            self.models[key] = model
            self.scalers[key] = scaler
    
    def predict(self, df_ventas, semanas_futuras=1):
        """
        Predice demanda futura con intervalos de confianza
        Retorna: predicción, intervalo inferior, intervalo superior
        """
        df_features = self.prepare_features(df_ventas)
        predictions = []
        
        feature_cols = ['ventas_lag1', 'ventas_lag2', 'media_movil_4', 
                        'std_movil_4', 'tendencia']
        
        for (tienda, producto), group in df_features.groupby(['id_tienda', 'id_producto']):
            key = f"{tienda}_{producto}"
            
            if key not in self.models:
                # Si no hay modelo, usar promedio histórico
                pred_mean = group['unidades_vendidas'].mean()
                pred_std = group['unidades_vendidas'].std()
                pred_mean = max(0, pred_mean)
                pred_std = max(1, pred_std)
            else:
                # Última fila para predicción
                last_row = group.iloc[-1:][feature_cols].values
                X_scaled = self.scalers[key].transform(last_row)
                
                # Predicción con árboles individuales para intervalo de confianza
                model = self.models[key]
                tree_preds = np.array([tree.predict(X_scaled)[0] 
                                      for tree in model.estimators_])
                
                pred_mean = np.mean(tree_preds)
                pred_std = np.std(tree_preds)
                pred_mean = max(0, pred_mean)
            
            # Intervalos de confianza (95%)
            pred_lower = max(0, pred_mean - 1.96 * pred_std)
            pred_upper = pred_mean + 1.96 * pred_std
            
            predictions.append({
                'id_tienda': tienda,
                'id_producto': producto,
                'demanda_pronosticada': pred_mean,
                'demanda_lower': pred_lower,
                'demanda_upper': pred_upper,
                'incertidumbre': pred_std
            })
        
        return pd.DataFrame(predictions)


class InventoryOptimizer:
    """
    Optimizador de inventario basado en Newsvendor Problem
    """
    def __init__(self, df_catalogo):
        self.df_catalogo = df_catalogo.set_index('id_producto')
    
    def calcular_costo_esperado(self, cantidad_pedido, demanda_pronostico, 
                                demanda_lower, demanda_upper, 
                                costo_unitario, precio_venta, 
                                costo_almacenamiento_semanal):
        """
        Calcula el costo total esperado usando distribución de probabilidad
        
        Parámetros:
        - cantidad_pedido: cantidad a pedir
        - demanda_pronostico: demanda esperada
        - demanda_lower, demanda_upper: intervalo de confianza
        - costo_unitario: costo de compra por unidad
        - precio_venta: precio de venta por unidad
        - costo_almacenamiento_semanal: costo de mantener inventario por semana
        """
        # Margen de ganancia por unidad vendida
        margen_unitario = precio_venta - costo_unitario
        
        # Costo de oportunidad por unidad no vendida (stockout)
        costo_stockout = margen_unitario
        
        # Costo de overstock por unidad sobrante
        costo_overstock = costo_unitario + costo_almacenamiento_semanal
        
        # Asumimos distribución normal truncada para la demanda
        # Usamos el intervalo de confianza para estimar std
        if demanda_upper > demanda_lower:
            std_demanda = (demanda_upper - demanda_lower) / (2 * 1.96)
        else:
            std_demanda = max(1, demanda_pronostico * 0.2)
        
        # Simulación Monte Carlo para calcular costo esperado
        n_sim = 1000
        demandas_sim = np.random.normal(
            demanda_pronostico, 
            std_demanda, 
            n_sim
        )
        demandas_sim = np.maximum(0, demandas_sim)  # No negativas
        
        costos = []
        for demanda_real in demandas_sim:
            if demanda_real > cantidad_pedido:
                # Stockout
                unidades_perdidas = demanda_real - cantidad_pedido
                costo = unidades_perdidas * costo_stockout
            else:
                # Overstock
                unidades_sobrantes = cantidad_pedido - demanda_real
                costo = unidades_sobrantes * costo_overstock
            
            costos.append(costo)
        
        costo_esperado = np.mean(costos)
        return costo_esperado
    
    def optimizar_cantidad_pedido(self, df_pronosticos, df_inventario):
        """
        Optimiza la cantidad de pedido para cada SKU-Tienda
        
        Estrategia adaptativa basada en:
        1. Ratio de margen (margen_unitario / costo_overstock)
        2. Incertidumbre del pronóstico
        3. Stock actual
        """
        resultados = []
        
        for _, row in df_pronosticos.iterrows():
            tienda = row['id_tienda']
            producto = row['id_producto']
            
            # Obtener información del producto
            prod_info = self.df_catalogo.loc[producto]
            costo_unitario = prod_info['costo_unitario']
            precio_venta = prod_info['precio_venta']
            costo_almacenamiento = prod_info['costo_almacenamiento_semanal']
            
            # Obtener stock actual
            stock_actual = df_inventario[
                (df_inventario['id_tienda'] == tienda) & 
                (df_inventario['id_producto'] == producto)
            ]['stock_actual'].values
            
            if len(stock_actual) == 0:
                stock_actual = 0
            else:
                stock_actual = stock_actual[0]
            
            # Parámetros del pronóstico
            demanda_pronostico = row['demanda_pronosticada']
            demanda_lower = row['demanda_lower']
            demanda_upper = row['demanda_upper']
            incertidumbre = row['incertidumbre']
            
            # Calcular ratio de margen
            margen_unitario = precio_venta - costo_unitario
            costo_overstock = costo_unitario + costo_almacenamiento
            ratio_margen = margen_unitario / costo_overstock if costo_overstock > 0 else 0
            
            # Coeficiente de agresividad basado en margen e incertidumbre
            # Productos con alto margen y baja incertidumbre -> más agresivo
            # Productos con bajo margen y alta incertidumbre -> más conservador
            if incertidumbre > 0:
                coeficiente_incertidumbre = demanda_pronostico / (demanda_pronostico + incertidumbre)
            else:
                coeficiente_incertidumbre = 1.0
            
            # Ajuste de agresividad: alto margen -> más agresivo
            factor_agresividad = min(1.5, max(0.5, ratio_margen * 2))
            
            # Demanda objetivo ajustada
            demanda_ajustada = demanda_pronostico * factor_agresividad * coeficiente_incertidumbre
            
            # Optimización: buscar cantidad que minimice costo esperado
            cantidades_a_probar = np.arange(
                max(0, int(demanda_lower)), 
                int(demanda_upper * 1.5) + 1, 
                1
            )
            
            mejor_cantidad = demanda_pronostico
            mejor_costo = float('inf')
            
            for cantidad in cantidades_a_probar:
                costo = self.calcular_costo_esperado(
                    cantidad,
                    demanda_pronostico,
                    demanda_lower,
                    demanda_upper,
                    costo_unitario,
                    precio_venta,
                    costo_almacenamiento
                )
                
                if costo < mejor_costo:
                    mejor_costo = costo
                    mejor_cantidad = cantidad
            
            # Calcular necesidad neta (considerando stock actual)
            necesidad_neta = max(0, mejor_cantidad - stock_actual)
            
            resultados.append({
                'id_tienda': tienda,
                'id_producto': producto,
                'stock_actual': stock_actual,
                'demanda_pronosticada': demanda_pronostico,
                'demanda_lower': demanda_lower,
                'demanda_upper': demanda_upper,
                'incertidumbre': incertidumbre,
                'cantidad_optima': mejor_cantidad,
                'cantidad_pedido': necesidad_neta,
                'ratio_margen': ratio_margen,
                'factor_agresividad': factor_agresividad,
                'costo_esperado': mejor_costo
            })
        
        return pd.DataFrame(resultados)


def main():
    """Función principal para ejecutar el pipeline completo"""
    
    # Cargar datos
    print("Cargando datos...")
    df_ventas = pd.read_csv('data/01_supply_optimization/ventas_historicas.csv')
    df_inventario = pd.read_csv('data/01_supply_optimization/inventario_actual.csv')
    df_catalogo = pd.read_csv('data/01_supply_optimization/catalogo_productos.csv')
    df_tiendas = pd.read_csv('data/01_supply_optimization/maestro_tiendas.csv')
    
    # Paso 1: Entrenar modelo de pronóstico
    print("Entrenando modelo de pronóstico...")
    forecaster = DemandForecaster()
    forecaster.train(df_ventas)
    
    # Paso 2: Generar pronósticos
    print("Generando pronósticos...")
    df_pronosticos = forecaster.predict(df_ventas, semanas_futuras=1)
    
    # Paso 3: Optimizar cantidades de pedido
    print("Optimizando cantidades de pedido...")
    optimizer = InventoryOptimizer(df_catalogo)
    df_resultados = optimizer.optimizar_cantidad_pedido(df_pronosticos, df_inventario)
    
    # Paso 4: Guardar resultados
    print("Guardando resultados...")
    df_resultados.to_csv('resultados_optimizacion_abastecimiento.csv', index=False)
    
    # Resumen
    print("\n=== RESUMEN DE OPTIMIZACIÓN ===")
    print(f"Total SKU-Tienda analizados: {len(df_resultados)}")
    print(f"Total unidades a pedir: {df_resultados['cantidad_pedido'].sum():.0f}")
    print(f"Costo total esperado: ${df_resultados['costo_esperado'].sum():,.0f}")
    print(f"\nTop 10 productos con mayor cantidad a pedir:")
    print(df_resultados.nlargest(10, 'cantidad_pedido')[
        ['id_tienda', 'id_producto', 'cantidad_pedido', 'demanda_pronosticada']
    ].to_string(index=False))
    
    return df_resultados


if __name__ == "__main__":
    resultados = main()