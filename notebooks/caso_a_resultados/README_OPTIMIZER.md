# 📦 Sistema de Optimización de Inventario

## Descripción General

Este sistema implementa un modelo de optimización de inventario basado en el **Modelo Newsvendor clásico**, diseñado para minimizar el costo total esperado al balancear:

- **Costo de Stockout (Cu)**: Margen perdido por cada unidad no vendida
- **Costo de Overstock (Co)**: Costo de mantener inventario excedente

## 🎯 Objetivo

Determinar la cantidad óptima de pedido **Q*** que minimiza:

```
Costo Total = E[Costo Stockout] + E[Costo Overstock]
```

## 📐 Modelo Matemático

### Fórmula Principal

La cantidad óptima se calcula como:

```
Q* = μ + z(p) · σ
```

Donde:
- **μ**: Media de la demanda pronosticada
- **σ**: Desviación estándar de la demanda (incertidumbre)
- **z(p)**: Cuantil de la distribución Normal estándar
- **p**: Critical fractile = Cu / (Cu + Co)

### Interpretación del Critical Fractile (p)

| Valor de p | Estrategia | Escenario |
|------------|-----------|-----------|
| **0.9 - 0.99** | Agresiva | Cu >> Co (productos de alto margen) |
| **0.5 - 0.8** | Balanceada | Cu ≈ Co |
| **0.1 - 0.5** | Conservadora | Co >> Cu (productos perecederos) |

## 🏗️ Arquitectura del Sistema

El sistema sigue principios de **separación de responsabilidades** y **buenas prácticas**:

```
DataSource → DemandForecaster → InventoryOptimizer → ReplenishmentPlanner
     ↓              ↓                   ↓                     ↓
  Ventas       (μ, σ)              Q* = f(μ,σ,Cu,Co)     Pedido = Q* - Stock
```

### Componentes

#### 1. `DataSource`
- **Responsabilidad**: Cargar y preparar datos
- **Inputs**: CSVs de ventas, inventario, catálogo, tiendas
- **Outputs**: DataFrames limpios y normalizados

#### 2. `DemandForecaster`
- **Responsabilidad**: Generar pronósticos con incertidumbre
- **Modelo**: Prophet con intervalos de confianza del 95%
- **Outputs**: (μ_semana, σ_semana) por SKU-tienda

#### 3. `InventoryOptimizer`
- **Responsabilidad**: Calcular cantidad óptima de pedido
- **Modelo**: Newsvendor con distribución Normal
- **Outputs**: `OptimizationResult` con Q*, pedido, costos esperados

#### 4. `ReplenishmentPlanner`
- **Responsabilidad**: Orquestar el pipeline completo
- **Outputs**: DataFrame con recomendaciones de pedido

## 🚀 Uso

### Uso Básico

```python
from data_source import DataSource
from forecast import DemandForecaster
from optimizer import InventoryOptimizer, ReplenishmentPlanner

# 1. Cargar datos
repo = DataSource(
    ventas_path='data/01_supply_optimization/ventas_historicas.csv',
    inventario_path='data/01_supply_optimization/inventario_actual.csv',
    catalogo_path='data/01_supply_optimization/catalogo_productos.csv',
    tiendas_path='data/01_supply_optimization/maestro_tiendas.csv',
).load()

# 2. Configurar componentes
forecaster = DemandForecaster(
    min_history_days=30,
    interval_width=0.95,
    weekly_seasonality=True
)

optimizer = InventoryOptimizer(
    z_clip=(-3, 3),
    sigma_min=0.1
)

# 3. Ejecutar optimización
planner = ReplenishmentPlanner(repo, forecaster, optimizer)
plan = planner.run(verbose=True)

# 4. Guardar resultados
plan.to_csv('resultados_plan_pedidos.csv', index=False)
```

### Uso Avanzado: Análisis de Sensibilidad

```python
# Ejemplo: ¿Cómo cambia Q* si la incertidumbre aumenta?
for sigma in [10, 20, 30, 40]:
    result = optimizer.compute_order_quantity(
        mu_week=100,
        sigma_week=sigma,
        stock_actual=20,
        margen_unitario=1500,
        costo_overstock_unitario=50
    )
    print(f"σ={sigma} → Q*={result.Q_objetivo:.1f}")
```

## 📊 Outputs

### DataFrame Principal

| Columna | Descripción |
|---------|-------------|
| `id_tienda` | Identificador de tienda |
| `id_producto` | Identificador de producto |
| `nombre` | Nombre del producto |
| `stock_actual` | Inventario actual |
| `Q_objetivo_semana` | Cantidad objetivo óptima (Q*) |
| `pedido_sugerido` | Cantidad a pedir (Q* - Stock) |
| `mu_semana` | Media de demanda pronosticada |
| `sigma_semana` | Desviación estándar de demanda |
| `p_critico_agresividad` | Critical fractile (0-1) |
| `service_level_approx` | Nivel de servicio aproximado |
| `costo_esperado_stockout` | Costo esperado de faltante |
| `costo_esperado_overstock` | Costo esperado de exceso |
| `costo_total_esperado` | Costo total esperado |

## ✅ Buenas Prácticas Implementadas

### 1. Validación Robusta de Inputs
```python
# Evitar valores negativos
mu_week = float(max(0.0, mu_week))
sigma_week = float(max(self.sigma_min, sigma_week))

# Clipear z-scores extremos
z = float(np.clip(z, self.z_clip[0], self.z_clip[1]))
```

### 2. Manejo de Casos Edge
- **Cu = Co = 0**: Fallback a estrategia conservadora (media)
- **Co = 0**: Ser agresivo (p = 0.99)
- **Cu = 0**: Ser conservador (p = 0.01)

### 3. Separación de Responsabilidades
- Cada clase tiene una responsabilidad única y bien definida
- Interfaces claras entre componentes
- Configuración mediante parámetros explícitos

### 4. Código Documentado
- Docstrings detallados
- Type hints para parámetros
- Comentarios explicativos en lógica compleja

### 5. Dataclasses para Resultados
```python
@dataclass
class OptimizationResult:
    Q_objetivo: float
    pedido_sugerido: float
    p_critico: float
    expected_stockout_cost: float
    expected_overstock_cost: float
    service_level_approx: float
```

## 📈 Casos de Uso

### Caso 1: Producto de Alto Margen (Agresivo)
```
Cu = $3000, Co = $20
→ p = 0.993
→ Q* = μ + 2.5σ (alto buffer)
Interpretación: Vale la pena arriesgarse a tener exceso
```

### Caso 2: Producto Perecedero (Conservador)
```
Cu = $1000, Co = $500
→ p = 0.667
→ Q* = μ + 0.4σ (buffer moderado)
Interpretación: Evitar desperdicios costosos
```

### Caso 3: Producto Estable (Baja Incertidumbre)
```
μ = 50, σ = 5
→ Q* ≈ μ + 0.8×5 = 54
Interpretación: Poca variabilidad, buffer pequeño
```

### Caso 4: Producto Volátil (Alta Incertidumbre)
```
μ = 50, σ = 30
→ Q* ≈ μ + 0.8×30 = 74
Interpretación: Alta variabilidad, buffer grande
```

## ⚠️ Supuestos y Limitaciones

### Supuestos
1. **Demanda Normal**: D ~ N(μ, σ²) - Razonable por CLT en agregación semanal
2. **Costos Lineales**: Cu y Co constantes por unidad
3. **Horizonte Single-Period**: Una semana a la vez
4. **Independencia**: SKU-tiendas optimizados independientemente

### Limitaciones
- No considera correlaciones entre productos
- No modela lead times variables
- No incluye restricciones de capacidad
- No optimiza inventario multi-período

## 🔬 Validación y Métricas

### Métricas Clave
- **Fill Rate**: % de demanda satisfecha
- **Stock-out Rate**: % de veces sin inventario
- **Costo Total Real**: Comparar con costo esperado
- **Precisión del Pronóstico**: MAPE, RMSE

### Sugerencias de Validación
```python
# Backtest: Comparar Q* con demanda real histórica
historical_demand = ...
recommended_Q = ...
stockouts = (historical_demand > recommended_Q).sum()
fill_rate = 1 - (stockouts / len(historical_demand))
```

## 🛠️ Próximos Pasos

### Corto Plazo
1. ✅ Implementar modelo base Newsvendor
2. ✅ Integrar con pronósticos Prophet
3. ✅ Crear notebook de análisis
4. ⏳ Validar con backtest histórico

### Mediano Plazo
5. Incluir restricciones de capacidad
6. Modelar lead times
7. Dashboard interactivo (Streamlit/Dash)
8. Alertas automáticas

### Largo Plazo
9. Optimización multi-producto con correlaciones
10. Inventario multi-echelón (bodega → tiendas)
11. Integración con ERP/WMS
12. Machine learning para calibración dinámica de costos

## 📚 Referencias

1. Arrow, K. J., Harris, T., & Marschak, J. (1951). "Optimal inventory policy." *Econometrica*, 250-272.
2. Silver, E. A., Pyke, D. F., & Thomas, D. J. (2016). *Inventory and production management in supply chains*. CRC Press.
3. Chopra, S., & Meindl, P. (2015). *Supply Chain Management: Strategy, Planning, and Operation*. Pearson.
4. Nahmias, S., & Olsen, T. L. (2015). *Production and operations analysis*. Waveland Press.

---

**Versión**: 1.0  
**Fecha**: Enero 2026  
**Autor**: Sistema de Optimización de Inventario - Tostao  
**Contacto**: [Tu contacto aquí]
