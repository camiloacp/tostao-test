"""
Ejemplo simple de uso del optimizador de inventario.

Este script demuestra cómo usar el modelo Newsvendor
sin necesidad de importar todo el pipeline completo.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class OptimizationResult:
    """Resultado de la optimización para un SKU-tienda específico."""
    Q_objetivo: float
    pedido_sugerido: float
    p_critico: float
    expected_stockout_cost: float
    expected_overstock_cost: float
    service_level_approx: float


class SimpleInventoryOptimizer:
    """
    Versión simplificada del optimizador para ejemplos.
    
    Implementa el modelo Newsvendor clásico:
    Q* = μ + z(p) · σ
    donde p = Cu / (Cu + Co)
    """
    
    def __init__(self, z_clip=(-3.0, 3.0), sigma_min=0.1):
        self.z_clip = z_clip
        self.sigma_min = sigma_min
    
    @staticmethod
    def _norm_ppf(p):
        """Inversa de la distribución normal estándar (aproximación de Acklam)."""
        from scipy.stats import norm
        return norm.ppf(p)
    
    @staticmethod
    def _loss_function(z):
        """Función de pérdida estándar L(z) = φ(z) - z·Φ(z)"""
        from scipy.stats import norm
        phi = norm.pdf(z)
        Phi = norm.cdf(z)
        return phi - z * (1 - Phi)
    
    def compute_order_quantity(
        self,
        mu_week,
        sigma_week,
        stock_actual,
        margen_unitario,
        costo_overstock_unitario,
    ):
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
        """
        mu_week = float(max(0.0, mu_week))
        sigma_week = float(max(self.sigma_min, sigma_week))
        stock_actual = float(max(0.0, stock_actual))
        Cu = float(max(0.0, margen_unitario))
        Co = float(max(0.0, costo_overstock_unitario))

        # Caso especial: sin costos definidos
        if Cu == 0 and Co == 0:
            Q = mu_week
            p = 0.5
        # Caso: overstock "gratis" (solo importa evitar stockouts)
        elif Cu > 0 and Co == 0:
            p = 0.99
            z = self._norm_ppf(p)
            Q = mu_week + z * sigma_week
        # Caso: understocking "gratis" (solo importa evitar overstocks)
        elif Cu == 0 and Co > 0:
            p = 0.01
            z = self._norm_ppf(p)
            Q = mu_week + z * sigma_week
        # Caso normal: balancear ambos costos
        else:
            p = Cu / (Cu + Co)  # Critical fractile
            p = float(np.clip(p, 0.01, 0.99))
            z = self._norm_ppf(p)
            z = float(np.clip(z, self.z_clip[0], self.z_clip[1]))
            Q = mu_week + z * sigma_week

        Q = max(0.0, float(Q))
        pedido = max(0.0, Q - stock_actual)
        
        # Calcular costos esperados
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


def ejemplo_basico():
    """Ejemplo básico: Un solo producto."""
    print("="*80)
    print("EJEMPLO 1: Producto Individual")
    print("="*80)
    
    optimizer = SimpleInventoryOptimizer(z_clip=(-3, 3), sigma_min=0.1)
    
    # Parámetros del producto
    mu_week = 100      # Demanda promedio semanal
    sigma_week = 20    # Desviación estándar
    stock_actual = 30  # Inventario actual
    Cu = 1500          # Margen unitario (precio - costo)
    Co = 50            # Costo de almacenamiento semanal
    
    # Calcular Q* óptimo
    result = optimizer.compute_order_quantity(
        mu_week=mu_week,
        sigma_week=sigma_week,
        stock_actual=stock_actual,
        margen_unitario=Cu,
        costo_overstock_unitario=Co
    )
    
    print(f"\n📊 Inputs:")
    print(f"  - Demanda esperada (μ): {mu_week} unidades/semana")
    print(f"  - Incertidumbre (σ): {sigma_week} unidades")
    print(f"  - Stock actual: {stock_actual} unidades")
    print(f"  - Margen unitario (Cu): ${Cu}")
    print(f"  - Costo overstock (Co): ${Co}")
    
    print(f"\n🎯 Resultados:")
    print(f"  - Critical fractile (p): {result.p_critico:.3f}")
    print(f"  - Estrategia: {'Agresiva' if result.p_critico > 0.8 else 'Conservadora' if result.p_critico < 0.6 else 'Balanceada'}")
    print(f"  - Q* óptimo: {result.Q_objetivo:.1f} unidades")
    print(f"  - Pedido sugerido: {result.pedido_sugerido:.1f} unidades")
    print(f"  - Nivel de servicio: {result.service_level_approx:.1%}")
    
    print(f"\n💰 Costos Esperados:")
    print(f"  - Costo stockout: ${result.expected_stockout_cost:.2f}")
    print(f"  - Costo overstock: ${result.expected_overstock_cost:.2f}")
    print(f"  - Costo total: ${result.expected_stockout_cost + result.expected_overstock_cost:.2f}")
    print()


def comparar_estrategias():
    """Ejemplo comparativo: Producto Premium vs. Perecedero."""
    print("="*80)
    print("EJEMPLO 2: Comparación de Estrategias")
    print("="*80)
    
    optimizer = SimpleInventoryOptimizer(z_clip=(-3, 3), sigma_min=0.1)
    
    # Parámetros base comunes
    mu_week = 50
    sigma_week = 15
    stock_actual = 10
    
    # Caso 1: Producto Premium (alto margen, bajo costo almacenamiento)
    result_premium = optimizer.compute_order_quantity(
        mu_week=mu_week,
        sigma_week=sigma_week,
        stock_actual=stock_actual,
        margen_unitario=3000,  # Alto margen
        costo_overstock_unitario=20   # Bajo costo
    )
    
    # Caso 2: Producto Perecedero (bajo margen, alto costo almacenamiento)
    result_perecedero = optimizer.compute_order_quantity(
        mu_week=mu_week,
        sigma_week=sigma_week,
        stock_actual=stock_actual,
        margen_unitario=1000,  # Margen moderado
        costo_overstock_unitario=500  # Alto costo si sobra
    )
    
    print(f"\n📦 Producto Premium (Cu=$3000, Co=$20):")
    print(f"  - p = {result_premium.p_critico:.3f} → Estrategia AGRESIVA")
    print(f"  - Q* = {result_premium.Q_objetivo:.1f}")
    print(f"  - Pedido = {result_premium.pedido_sugerido:.1f}")
    
    print(f"\n🥐 Producto Perecedero (Cu=$1000, Co=$500):")
    print(f"  - p = {result_perecedero.p_critico:.3f} → Estrategia CONSERVADORA")
    print(f"  - Q* = {result_perecedero.Q_objetivo:.1f}")
    print(f"  - Pedido = {result_perecedero.pedido_sugerido:.1f}")
    
    print(f"\n💡 Observación:")
    print(f"   Con la misma demanda (μ={mu_week}, σ={sigma_week}),")
    print(f"   la estrategia agresiva pide {result_premium.pedido_sugerido - result_perecedero.pedido_sugerido:.1f} unidades más")
    print(f"   debido al mayor margen y menor costo de almacenamiento.")
    print()


def analisis_sensibilidad_incertidumbre():
    """Ejemplo: Impacto de la incertidumbre en Q*."""
    print("="*80)
    print("EJEMPLO 3: Impacto de la Incertidumbre")
    print("="*80)
    
    optimizer = SimpleInventoryOptimizer(z_clip=(-3, 3), sigma_min=0.1)
    
    mu_week = 100
    Cu = 1500
    Co = 50
    stock_actual = 0
    
    print(f"\nDemanda esperada: μ = {mu_week}")
    print(f"Costos: Cu = ${Cu}, Co = ${Co}")
    print("\nVariando la incertidumbre (σ):\n")
    
    for sigma in [10, 20, 30, 40]:
        result = optimizer.compute_order_quantity(
            mu_week=mu_week,
            sigma_week=sigma,
            stock_actual=stock_actual,
            margen_unitario=Cu,
            costo_overstock_unitario=Co
        )
        
        cv = sigma / mu_week
        buffer = result.Q_objetivo - mu_week
        
        print(f"  σ = {sigma:2d} (CV={cv:.2f}) → Q* = {result.Q_objetivo:6.1f} (buffer = {buffer:5.1f})")
    
    print(f"\n💡 Observación:")
    print(f"   A mayor incertidumbre, se requiere un buffer mayor de seguridad")
    print(f"   para mantener el mismo nivel de servicio.")
    print()


if __name__ == "__main__":
    print("\n🚀 Ejemplos de Uso del Optimizador de Inventario\n")
    
    ejemplo_basico()
    comparar_estrategias()
    analisis_sensibilidad_incertidumbre()
    
    print("="*80)
    print("✅ Ejemplos completados")
    print("="*80)
    print("\nPara ver el análisis completo con datos reales, ejecuta el notebook:")
    print("  jupyter notebook notebooks/caso_a_optimizer.ipynb")
    print("\nO ejecuta el script principal:")
    print("  python src/optimizer.py")
    print()

# python notebooks/ejemplo_simple_optimizer.py