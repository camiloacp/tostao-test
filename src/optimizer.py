from dataclasses import dataclass
from typing import Optional, Tuple, Dict
import numpy as np
import pandas as pd
import warnings

from data_source import DataSource
from forecast import DemandForecaster


@dataclass
class OptimizationResult:
    """Resultado de la optimización para un SKU-tienda específico."""
    Q_objetivo: float          # Cantidad objetivo de inventario
    pedido_sugerido: float     # Cantidad a pedir
    p_critico: float          # Critical fractile (agresividad)
    expected_stockout_cost: float    # Costo esperado de faltante
    expected_overstock_cost: float   # Costo esperado de exceso
    service_level_approx: float      # Nivel de servicio aproximado


class InventoryOptimizer:
    """
    Optimización de inventario basada en el modelo Newsvendor clásico.
    
    Objetivo: Minimizar el costo total esperado balanceando:
    - Costo de Stockout (Cu): margen perdido por unidad no vendida
    - Costo de Overstock (Co): costo de mantener inventario excedente
    
    Modelo:
    -------
    La cantidad óptima Q* se obtiene como el cuantil p de la demanda pronosticada:
        Q* = μ + z(p) · σ
    
    donde p (critical fractile) se calcula como:
        p = Cu / (Cu + Co)
    
    Interpretación:
    ---------------
    - p cercano a 1: Ser agresivo (Cu >> Co), pedir más para evitar faltantes
    - p cercano a 0.5: Balanceado (Cu ≈ Co), pedir cerca de la media
    - p cercano a 0: Ser conservador (Co >> Cu), pedir menos para evitar excesos
    
    Parámetros:
    -----------
    z_clip : tuple
        Rango de recorte para el z-score, evita pedidos extremos.
        Por defecto (-3, 3) equivale a cuantiles entre 0.13% y 99.87%.
    sigma_min : float
        Desviación estándar mínima para evitar divisiones por cero.
    """

    def __init__(
        self, 
        z_clip: Tuple[float, float] = (-3.0, 3.0),
        sigma_min: float = 0.1
    ):
        if z_clip[0] >= z_clip[1]:
            raise ValueError("z_clip[0] debe ser menor que z_clip[1]")
        self.z_clip = z_clip
        self.sigma_min = sigma_min

    @staticmethod
    def _norm_ppf(p: float) -> float:
        # Inversa de normal estándar vía scipy si existiera; aquí evitamos dependencia:
        # Aproximación de Peter John Acklam (suficiente para cuantiles).
        # Fuente de aproximaciones ampliamente usadas en cuant finance.
        # Nota: para entrevista, puedes reemplazar por scipy.stats.norm.ppf.
        if p <= 0.0:
            return -np.inf
        if p >= 1.0:
            return np.inf

        # Coeficientes Acklam
        a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
        b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
        d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00]

        plow = 0.02425
        phigh = 1 - plow

        if p < plow:
            q = np.sqrt(-2*np.log(p))
            num = (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5])
            den = ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
            return num / den
        if p > phigh:
            q = np.sqrt(-2*np.log(1-p))
            num = -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5])
            den = ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
            return num / den

        q = p - 0.5
        r = q*q
        num = (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q
        den = (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)
        return num / den

    def compute_order_quantity(
        self,
        mu_week: float,
        sigma_week: float,
        stock_actual: float,
        margen_unitario: float,
        costo_overstock_unitario: float,
    ) -> OptimizationResult:
        """
        Calcula la cantidad óptima de pedido según el modelo Newsvendor.
        
        Parámetros:
        -----------
        mu_week : float
            Media de la demanda semanal pronosticada
        sigma_week : float
            Desviación estándar de la demanda semanal pronosticada
        stock_actual : float
            Inventario actual disponible
        margen_unitario : float
            Costo de oportunidad por unidad faltante (Cu = precio - costo)
        costo_overstock_unitario : float
            Costo por mantener una unidad en inventario por semana (Co)
            
        Retorna:
        --------
        OptimizationResult con la cantidad objetivo, pedido sugerido y métricas
        """
        # Validación y normalización de inputs
        mu_week = float(max(0.0, mu_week))
        sigma_week = float(max(self.sigma_min, sigma_week))
        stock_actual = float(max(0.0, stock_actual))
        Cu = float(max(0.0, margen_unitario))
        Co = float(max(0.0, costo_overstock_unitario))

        # Caso especial: sin costos definidos
        if Cu == 0 and Co == 0:
            warnings.warn("Cu y Co son ambos cero. Usando estrategia conservadora (media).")
            Q = mu_week
            p = 0.5
        # Caso: overstock "gratis" (solo importa evitar stockouts)
        elif Cu > 0 and Co == 0:
            p = 0.99  # Ser muy agresivo
            z = self._norm_ppf(p)
            Q = mu_week + z * sigma_week
        # Caso: understocking "gratis" (solo importa evitar overstocks)
        elif Cu == 0 and Co > 0:
            p = 0.01  # Ser muy conservador
            z = self._norm_ppf(p)
            Q = mu_week + z * sigma_week
        # Caso normal: balancear ambos costos
        else:
            p = Cu / (Cu + Co)  # Critical fractile
            p = float(np.clip(p, 0.01, 0.99))  # Evitar extremos
            z = self._norm_ppf(p)
            z = float(np.clip(z, self.z_clip[0], self.z_clip[1]))
            Q = mu_week + z * sigma_week

        Q = max(0.0, float(Q))
        pedido = max(0.0, Q - stock_actual)
        
        # Calcular costos esperados (simplificado)
        # Usando aproximación Normal para el modelo Newsvendor
        service_level = p
        expected_stockout_cost = Cu * sigma_week * self._loss_function(z) if Cu > 0 else 0.0
        expected_overstock_cost = Co * sigma_week * self._loss_function(-z) if Co > 0 else 0.0

        return OptimizationResult(
            Q_objetivo=Q,
            pedido_sugerido=pedido,
            p_critico=p,
            expected_stockout_cost=expected_stockout_cost,
            expected_overstock_cost=expected_overstock_cost,
            service_level_approx=service_level
        )
    
    @staticmethod
    def _loss_function(z: float) -> float:
        """
        Función de pérdida estándar L(z) = φ(z) - z·Φ(z)
        donde φ es la PDF y Φ es la CDF de la Normal(0,1).
        
        Esta función es clave en el modelo Newsvendor para calcular
        el stockout esperado.
        """
        from scipy.stats import norm
        phi = norm.pdf(z)
        Phi = norm.cdf(z)
        return phi - z * (1 - Phi)


# ----------------------------
# Orchestration
# ----------------------------

class ReplenishmentPlanner:
    """
    Orquestador principal que integra pronósticos y optimización de inventario.
    
    Flujo:
    1. Obtiene ventas históricas del repositorio
    2. Genera pronósticos de demanda con incertidumbre (μ, σ)
    3. Calcula la política óptima de pedidos usando el modelo Newsvendor
    4. Retorna recomendaciones de pedido por SKU-tienda
    """
    
    def __init__(
        self,
        repo: DataSource,
        forecaster: DemandForecaster,
        optimizer: InventoryOptimizer,
    ):
        self.repo = repo
        self.forecaster = forecaster
        self.optimizer = optimizer

    def run(self, verbose: bool = False) -> pd.DataFrame:
        """
        Ejecuta el pipeline completo de optimización de inventario.
        
        Parámetros:
        -----------
        verbose : bool
            Si True, imprime información de progreso
            
        Retorna:
        --------
        DataFrame con recomendaciones de pedido para cada SKU-tienda
        """
        if verbose:
            print("📊 Cargando datos históricos de ventas...")
        sales_panel = self.repo.sales_daily()
        
        if verbose:
            print("🔮 Generando pronósticos de demanda con incertidumbre...")
        forecast = self.forecaster.fit_predict_week(sales_panel)
        
        if verbose:
            print("📦 Cargando inventario y costos actuales...")
        master = self.repo.master_store()

        # Unir forecast con tabla de stock/costos
        df = master.merge(
            forecast,
            on=["id_tienda", "id_producto"],
            how="left",
        )

        # Si algún SKU-tienda no tuvo ventas históricas, asumir demanda 0 con sigma mínima
        df["mu_semana"] = df["mu_semana"].fillna(0.0)
        df["sigma_semana"] = df["sigma_semana"].fillna(1.0)

        if verbose:
            print(f"⚙️  Optimizando política de pedidos para {len(df)} SKU-tiendas...")
        
        # Calcular política óptima
        results = []
        for row in df.itertuples(index=False):
            opt_result = self.optimizer.compute_order_quantity(
                mu_week=row.mu_semana,
                sigma_week=row.sigma_semana,
                stock_actual=row.stock_actual,
                margen_unitario=row.margen_unitario,
                costo_overstock_unitario=row.costo_overstock,
            )
            results.append(opt_result)

        # Agregar resultados al dataframe
        df["Q_objetivo_semana"] = [r.Q_objetivo for r in results]
        df["pedido_sugerido"] = [r.pedido_sugerido for r in results]
        df["p_critico_agresividad"] = [r.p_critico for r in results]
        df["service_level_approx"] = [r.service_level_approx for r in results]
        df["costo_esperado_stockout"] = [r.expected_stockout_cost for r in results]
        df["costo_esperado_overstock"] = [r.expected_overstock_cost for r in results]
        df["costo_total_esperado"] = (
            df["costo_esperado_stockout"] + df["costo_esperado_overstock"]
        )

        # Salida amigable
        cols = [
            "id_tienda", "id_producto", "nombre",
            "stock_actual", "Q_objetivo_semana", "pedido_sugerido",
            "mu_semana", "sigma_semana",
            "margen_unitario", "costo_overstock",
            "p_critico_agresividad", "service_level_approx",
            "costo_esperado_stockout", "costo_esperado_overstock", "costo_total_esperado",
            "ciudad", "tamaño_m2",
        ]
        
        result_df = df[cols].sort_values(["id_tienda", "id_producto"]).reset_index(drop=True)
        
        if verbose:
            print(f"✅ Optimización completada!")
            print(f"   Total a pedir: {result_df['pedido_sugerido'].sum():.0f} unidades")
            print(f"   Costo total esperado: ${result_df['costo_total_esperado'].sum():,.0f}")
        
        return result_df


# ----------------------------
# Example usage
# ----------------------------

if __name__ == "__main__":
    import os
    
    # Configurar rutas relativas
    base_path = os.path.join(os.path.dirname(__file__), "..", "data", "01_supply_optimization")
    
    repo = DataSource(
        ventas_path=os.path.join(base_path, "ventas_historicas.csv"),
        inventario_path=os.path.join(base_path, "inventario_actual.csv"),
        catalogo_path=os.path.join(base_path, "catalogo_productos.csv"),
        tiendas_path=os.path.join(base_path, "maestro_tiendas.csv"),
    ).load()

    forecaster = DemandForecaster(
        min_history_days=30,
        interval_width=0.95,
        weekly_seasonality=True,
        changepoint_prior_scale=0.05
    )
    
    optimizer = InventoryOptimizer(
        z_clip=(-3, 3),
        sigma_min=0.1
    )

    planner = ReplenishmentPlanner(repo, forecaster, optimizer)
    plan = planner.run(verbose=True)

    # Guardar resultados
    output_path = os.path.join(os.path.dirname(__file__), "..", "notebooks", "plan_pedidos_semana.csv")
    plan.to_csv(output_path, index=False)
    
    print("\n" + "="*80)
    print("RESUMEN DE RECOMENDACIONES")
    print("="*80)
    print(plan.head(20))
    print("\n" + "="*80)
    print(f"Total SKU-tiendas: {len(plan)}")
    print(f"Total unidades a pedir: {plan['pedido_sugerido'].sum():.0f}")
    print(f"Costo total esperado: ${plan['costo_total_esperado'].sum():,.2f}")
    print("="*80)