# Caso B: Creación de Combos de Productos

## 📋 Descripción General

Este análisis identifica los **Top 5 combos de productos** con mayor potencial de venta para diferentes clusters de tiendas, cuantificando el lift esperado y proponiendo precios óptimos.

---

## 🎯 Objetivo

Identificar combinaciones de productos que:

1. Se compran frecuentemente juntos (support)
2. Tienen alta correlación de compra conjunta (confidence)
3. Presentan fuerte potencial de venta cruzada (lift)
4. Pueden ser ofrecidos con descuentos atractivos manteniendo rentabilidad

---

## 📊 Metodología

### 1. **Análisis Exploratorio de Datos (EDA)**

- Carga y exploración de datasets
- Análisis de frecuencia de productos
- Identificación de patrones de compra

### 2. **Clustering de Tiendas**

- Segmentación de 20 tiendas en 7 clusters mediante K-Means
- Features utilizados:
  - Número de tickets
  - Ventas totales
  - Ticket promedio
  - Items por ticket
  - Mix de categorías (Bebidas vs Alimentos)
- Selección de número óptimo de clusters mediante:
  - Método del codo
  - Silhouette Score

### 3. **Market Basket Analysis**

- Algoritmo: **FP-Growth**
- Generación de reglas de asociación
- Métricas calculadas:
  - **Support**: Frecuencia de co-ocurrencia (% de tickets)
  - **Confidence**: Probabilidad de compra conjunta
  - **Lift**: Potencial de venta cruzada (factor de mejora)

### 4. **Filtrado de Ruido**

- Eliminación de productos con:
  - Alta frecuencia global (>25% de tickets)
  - Baja correlación específica (lift < 1.5)
- Retención de combos con verdadero potencial

### 5. **Propuesta de Precios**

Estrategia de pricing basada en lift:

- **Lift alto (>2.5)**: 15-20% descuento
- **Lift medio (1.5-2.5)**: 10-15% descuento
- **Lift bajo (1.2-1.5)**: 5-10% descuento

Ajustes:

- Mayor confianza = menor descuento necesario
- Precios redondeados a múltiplos de $100

### 6. **Ranking y Selección**

Score compuesto (0-100):

- Lift: 40% del peso
- Support: 30% del peso
- Confidence: 20% del peso
- Descuento: 10% del peso

---

## 📁 Datasets Utilizados

### Entrada

- `data/02_product_bundles/tickets.csv`
  - Información de tickets: id_ticket, id_tienda, id_cliente, fecha, total
- `data/02_product_bundles/detalle_tickets.csv`
  - Detalle de productos por ticket: id_ticket, id_producto, cantidad, precio_unitario
- `data/02_product_bundles/catalogo_productos.csv`
  - Catálogo de productos: id_producto, nombre, categoria, subcategoria

### Salida

- `caso_b_resultados/top_5_combos_por_cluster.csv`
  - Top 5 combos por cada uno de los 7 clusters
  - Columnas:
    - cluster_id: ID del cluster de tiendas
    - combo_rank: Posición del combo (1-5)
    - productos: Nombres de productos en el combo
    - productos_ids: IDs de productos
    - categorias: Categorías de productos
    - num_productos: Cantidad de productos en el combo
    - precio_individual_total: Suma de precios individuales
    - precio_combo_propuesto: Precio del combo con descuento
    - descuento_pct: Porcentaje de descuento aplicado
    - ahorro_cliente: Ahorro en pesos para el cliente
    - lift: Factor de potencial de venta cruzada
    - support: Frecuencia de co-ocurrencia
    - confidence: Probabilidad de compra conjunta
    - score: Score compuesto (0-100)

---

## 📈 Resultados Principales

### Estadísticas Globales

- **7 clusters** de tiendas identificados
- **35 combos** recomendados en total
- **Lift promedio**: 6.77x (los productos tienen casi 7 veces más probabilidad de venderse juntos)
- **Precio combo promedio**: $5,609
- **Descuento promedio**: 16.2%
- **Ahorro promedio**: $1,086

### Top 3 Combos Globales (por score)

#### 🥇 Combo #1 - Cluster 4

- **Productos**: Avena + Buñuelo
- **Lift**: 9.98x ⭐⭐⭐
- **Support**: 5.0%
- **Confidence**: 86.7%
- **Precio**: $5,100 (descuento 15.8%)
- **Score**: 66.0/100

#### 🥈 Combo #2 - Cluster 3

- **Productos**: Café con Leche + Almojábana
- **Lift**: 7.86x ⭐⭐⭐
- **Support**: 5.7%
- **Confidence**: 78.3%
- **Precio**: $5,300 (descuento 15.9%)
- **Score**: 64.6/100

#### 🥉 Combo #3 - Cluster 1

- **Productos**: Pan de Bono + Tinto
- **Lift**: 5.09x ⭐⭐
- **Support**: 5.6%
- **Confidence**: 76.4%
- **Precio**: $4,500 (descuento 16.0%)
- **Score**: 64.3/100

---

## 🏆 Características de los Clusters

| Cluster | Tiendas | Ticket Promedio | Items/Ticket | Mix Alimentos/Bebidas |
| ------- | ------- | --------------- | ------------ | --------------------- |
| 0       | 2       | $3,517          | 1.86         | 52% / 48%             |
| 1       | 6       | $3,465          | 1.88         | 51% / 50%             |
| 2       | 4       | $3,472          | 1.94         | 51% / 49%             |
| 3       | 2       | $3,442          | 1.85         | 49% / 51%             |
| 4       | 3       | $3,481          | 1.86         | 52% / 49%             |
| 5       | 2       | $3,490          | 1.90         | 50% / 50%             |
| 6       | 1       | $3,431          | 1.93         | 54% / 46%             |

---

## 💡 Insights Clave

### Patrones de Compra Identificados

1. **Combos Bebida + Alimento**: Dominan los top combos

   - Tinto + Pan de Bono
   - Café con Leche + Almojábana
   - Cappuccino + Croissant de Queso
   - Avena + Buñuelo

2. **Lift Alto (>2.5x)**:

   - Indica fuerte preferencia de compra conjunta
   - Cliente que compra producto A tiene 2.5x+ probabilidad de comprar producto B

3. **Support Moderado (3-6%)**:

   - Los combos ya ocurren naturalmente en 3-6% de tickets
   - Espacio para crecimiento significativo mediante promoción

4. **Descuentos Estratégicos (15-17%)**:
   - Balancean atractivo para cliente con rentabilidad
   - Basados en lift: mayor potencial = mayor incentivo

---

## 🚀 Recomendaciones de Implementación

### Fase 1: Piloto (4-6 semanas)

**Objetivo**: Validar hipótesis con datos reales

**Acciones**:

1. Seleccionar cluster con mayor score (Cluster 4)
2. Implementar Top 3 combos en tiendas del cluster
3. Crear material promocional:
   - Menús/displays visuales
   - Sugerencias en POS
   - Capacitación de personal

**Métricas a Monitorear**:

- Tasa de adopción de combos
- Impacto en ticket promedio
- Frecuencia de compra por cliente
- Satisfacción del cliente (NPS)
- Margen de contribución por combo

**Target de Éxito**:

- ≥20% de adopción en primeras 4 semanas
- +5-10% en ticket promedio
- Mantener o mejorar margen de contribución

### Fase 2: Expansión (2-3 meses)

**Acciones**:

1. Roll out gradual por clusters según score
2. Personalizar combos por cluster
3. Ajustar precios según respuesta del mercado
4. Implementar A/B testing de variaciones

**Optimizaciones**:

- Testear descuentos alternos (±2%)
- Probar combos de 3 productos
- Analizar performance por horario/día
- Segmentar por tipo de cliente

### Fase 3: Optimización Continua

**Acciones**:

1. Dashboard en tiempo real con KPIs
2. Re-entrenamiento trimestral del modelo
3. Incorporar nuevos productos estacionales
4. Análisis de canibalización

**KPIs Críticos**:

- Adopción de combos vs meta
- Incremento en ticket promedio
- Rentabilidad por combo
- Satisfacción del cliente
- Frecuencia de recompra

---

## 📊 Impacto Financiero Estimado

### Supuestos Base

- **10,000 tickets** totales analizados
- **Ticket promedio actual**: $3,465
- **Items por ticket**: 1.84

### Escenario Conservador (20% adopción)

- Combos vendidos/mes: 2,000
- Incremento en ticket: +$800/combo
- **Impacto mensual**: +$1,600,000
- **Impacto anual**: ~$19,200,000

### Escenario Optimista (30% adopción)

- Combos vendidos/mes: 3,000
- Incremento en ticket: +$800/combo
- **Impacto mensual**: +$2,400,000
- **Impacto anual**: ~$28,800,000

_Nota: Impactos estimados sin considerar costos adicionales de operación_

---

## 🛠️ Requisitos Técnicos

### Librerías Python

```python
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
scikit-learn>=1.3.0
mlxtend>=0.22.0  # Para FP-Growth
```

### Instalación

```bash
pip install pandas numpy matplotlib seaborn scikit-learn mlxtend
```

---

## 🎯 Cómo Ejecutar el Notebook

### Paso 1: Preparación

```bash
# Activar entorno virtual
source test-tostao/bin/activate  # Linux/Mac
# o
test-tostao\Scripts\activate  # Windows

# Navegar a directorio
cd notebooks
```

### Paso 2: Ejecución

```bash
# Abrir Jupyter
jupyter notebook caso_b.ipynb

# Ejecutar todas las celdas: Cell > Run All
```

### Paso 3: Verificar Outputs

- Archivo generado: `caso_b_resultados/top_5_combos_por_cluster.csv`
- Visualizaciones en el notebook
- Resumen ejecutivo al final

---

## 📁 Estructura de Archivos

```
notebooks/
├── caso_b.ipynb                          # Notebook principal
└── caso_b_resultados/
    ├── top_5_combos_por_cluster.csv      # Resultados exportados
    └── README.md                          # Este archivo
```

---

## 🔍 Interpretación de Métricas

### Lift

- **Definición**: Factor de mejora en probabilidad de compra conjunta
- **>2.5**: ⭐⭐⭐ Alto potencial
- **1.5-2.5**: ⭐⭐ Potencial moderado-alto
- **1.2-1.5**: ⭐ Potencial moderado

### Support

- **Definición**: % de tickets en que ocurre el combo
- **>5%**: Frecuencia alta (ya existe comportamiento natural)
- **2-5%**: Frecuencia moderada (espacio para crecimiento)
- **<2%**: Frecuencia baja (nicho o producto nuevo)

### Confidence

- **Definición**: P(comprar B | compró A)
- **>70%**: Alta probabilidad de compra conjunta
- **50-70%**: Probabilidad moderada
- **<50%**: Probabilidad baja (requiere incentivo)

### Score

- **Definición**: Métrica compuesta (0-100)
- **Formula**: 0.4×Lift + 0.3×Support + 0.2×Confidence + 0.1×Descuento
- **>60**: Combo altamente recomendado
- **50-60**: Buen potencial
- **<50**: Considerar con precaución

---

## 💰 Estrategia de Pricing

### Principios

1. **Incentivo basado en lift**: Mayor lift = mayor descuento
2. **Ajuste por confianza**: Alta confianza = menor descuento necesario
3. **Límites**: 5% mínimo, 20% máximo
4. **Redondeo**: Múltiplos de $100 para facilitar comunicación

### Rangos de Descuento

```
Lift > 2.5    → 15-20% descuento
Lift 2.0-2.5  → 10-15% descuento
Lift 1.5-2.0  → 7-12% descuento
Lift 1.2-1.5  → 5-10% descuento
```

---

## 📦 Ejemplos de Combos Recomendados

### Combo Premium - Cluster 4

**Productos**: Avena + Buñuelo  
**Precio Individual**: $6,000  
**Precio Combo**: $5,100 (15.8% descuento)  
**Lift**: 9.98x ⭐⭐⭐  
**Interpretación**: Cliente que compra Avena tiene casi 10x más probabilidad de comprar Buñuelo

### Combo Desayuno - Cluster 3

**Productos**: Café con Leche + Almojábana  
**Precio Individual**: $6,300  
**Precio Combo**: $5,300 (15.9% descuento)  
**Lift**: 7.86x ⭐⭐⭐  
**Interpretación**: Fuerte correlación de compra en horario matutino

### Combo Clásico - Cluster 1

**Productos**: Pan de Bono + Tinto  
**Precio Individual**: $5,300  
**Precio Combo**: $4,500 (16.0% descuento)  
**Lift**: 5.09x ⭐⭐  
**Interpretación**: Combo tradicional con alta adopción (5.6% de tickets)

---

## ⚠️ Limitaciones y Consideraciones

### Limitaciones del Análisis

1. **Tamaño de muestra**: 10,000 tickets (1 año)

   - Considerar análisis continuo con más data
   - Validar estacionalidad

2. **Clusters estáticos**: Tiendas pueden cambiar perfil

   - Re-clustering trimestral recomendado

3. **Precios estimados**: Basados en promedios

   - Ajustar según costos específicos por tienda

4. **No considera**:
   - Márgenes de contribución específicos
   - Disponibilidad de inventario
   - Restricciones operativas

### Factores Externos a Considerar

**Operacionales**:

- Capacidad de preparación simultánea
- Tiempo de espera en horas pico
- Disponibilidad de ingredientes

**Comerciales**:

- Competencia y precios de mercado
- Percepción de valor por cliente
- Impacto en productos individuales

**Financieros**:

- Margen de contribución por combo
- Costos de implementación (marketing, POS)
- Canibalización de ventas individuales

---

## 📋 Checklist de Implementación

### Pre-Lanzamiento

- [ ] Validar combos con equipos de operaciones
- [ ] Verificar disponibilidad de productos
- [ ] Calcular márgenes de contribución reales
- [ ] Definir tiendas piloto (cluster 4 recomendado)
- [ ] Diseñar materiales promocionales
- [ ] Configurar combos en sistema POS
- [ ] Capacitar personal de tienda
- [ ] Establecer KPIs y dashboard de seguimiento

### Lanzamiento

- [ ] Comunicación interna (kickoff)
- [ ] Activación en tiendas piloto
- [ ] Monitoreo diario primeros 7 días
- [ ] Recolección de feedback de clientes y empleados
- [ ] Ajustes rápidos si es necesario

### Post-Lanzamiento (Semana 4-6)

- [ ] Análisis de resultados vs targets
- [ ] Identificar combos ganadores/perdedores
- [ ] Ajustar precios/descuentos según data
- [ ] Plan de expansión a otros clusters

---

## 📊 Dashboard de Seguimiento Sugerido

### Métricas Diarias

- Combos vendidos por tienda
- Tasa de adopción (% de tickets con combo)
- Ticket promedio con/sin combo
- Top combos por tienda

### Métricas Semanales

- Tendencia de adopción
- Impacto en ventas totales
- Rentabilidad por combo
- Análisis de horarios/días pico

### Métricas Mensuales

- Performance vs forecast
- Comparativa entre clusters
- ROI de la iniciativa
- Recomendaciones de optimización

---

## 🔬 Mejoras Futuras

### Enriquecimiento de Datos

1. **Datos de clientes**:

   - Segmentación por edad/género
   - Frecuencia de visita
   - Productos favoritos

2. **Datos contextuales**:

   - Horario de compra
   - Día de la semana
   - Clima/temperatura
   - Eventos especiales

3. **Datos de inventario**:
   - Disponibilidad de productos
   - Tiempos de preparación
   - Costos variables

### Análisis Avanzados

1. **Combos de 3+ productos**: Analizar bundling más complejo
2. **Descuentos dinámicos**: Ajuste según hora/día/inventario
3. **Personalización**: Combos sugeridos por perfil de cliente
4. **Cross-selling digital**: Integración con app/web

---

## 👥 Equipo y Responsabilidades

### Data Science

- Mantenimiento del modelo
- Análisis de resultados
- Optimización continua

### Producto/Marketing

- Diseño de campaña
- Materiales promocionales
- Comunicación al cliente

### Operaciones

- Implementación en tiendas
- Capacitación de personal
- Logística y disponibilidad

### Finanzas

- Análisis de rentabilidad
- Tracking de ROI
- Forecasting de impacto

---

## 📞 Contacto y Soporte

Para dudas o consultas sobre este análisis:

- **Autor**: Data Science Team
- **Notebook**: `caso_b.ipynb`
- **Última actualización**: Diciembre 2024

---

## 📝 Notas Técnicas

### Parámetros del Modelo

**FP-Growth**:

```python
min_support = 0.01      # Mínimo 1% de tickets
min_threshold = 1.2     # Lift mínimo 1.2x
max_len = 3             # Combos de 2-3 productos
```

**K-Means**:

```python
n_clusters = 7          # Óptimo según silhouette
random_state = 42       # Reproducibilidad
n_init = 10             # Inicializaciones
```

**Score Compuesto**:

```python
score = (0.40 * lift_normalized +
         0.30 * support +
         0.20 * confidence +
         0.10 * discount_normalized) * 100
```

### Tiempo de Ejecución

- Análisis completo: ~5-10 minutos
- Clustering: ~30 segundos
- Market Basket Analysis por cluster: ~1 minuto
- Exportación: <5 segundos

---

## 🔄 Historial de Versiones

### v1.0 (Diciembre 2024)

- ✅ Implementación inicial
- ✅ 7 clusters identificados
- ✅ 35 combos recomendados
- ✅ Estrategia de pricing definida
- ✅ Exportación a CSV

### Roadmap v2.0

- [ ] Análisis de estacionalidad
- [ ] Combos de 3+ productos
- [ ] Integración con datos de clientes
- [ ] Dashboard interactivo
- [ ] API para consulta en tiempo real

---

## ⚖️ Disclaimer

Este análisis es una recomendación basada en datos históricos y técnicas de machine learning. Los resultados reales pueden variar según:

- Cambios en comportamiento de clientes
- Factores externos (competencia, economía)
- Calidad de ejecución de la estrategia
- Disponibilidad de productos

Se recomienda validación mediante piloto antes de implementación masiva.

---

## 📚 Referencias

### Algoritmos Utilizados

- **K-Means Clustering**: Segmentación de tiendas
- **FP-Growth**: Market Basket Analysis
- **Association Rules**: Generación de reglas de asociación

### Métricas de Negocio

- **Lift**: Potencial de venta cruzada
- **Support**: Frecuencia de co-ocurrencia
- **Confidence**: Probabilidad condicional
- **ROI**: Retorno de inversión

### Papers/Recursos

- Agrawal & Srikant (1994): "Fast Algorithms for Mining Association Rules"
- Han et al. (2000): "Mining Frequent Patterns without Candidate Generation"
- Tutorial: Market Basket Analysis with Python (mlxtend documentation)

---

**Última Actualización**: Diciembre 2024  
**Versión**: 1.0  
**Autor**: Data Science Team - Tostao  
**Status**: ✅ Completado - Listo para Implementación
