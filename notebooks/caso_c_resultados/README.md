# Caso C: Resultados - Modelado de Ticket Promedio (AOV Drivers)

## 📁 Contenido de esta Carpeta

Esta carpeta contiene los resultados del análisis del **Caso C: Modelado de Ticket Promedio (AOV Drivers)**, parte de la Prueba Técnica de Data Science & ML para Tostao.

---

## 📄 Archivos Disponibles

### 1. RESUMEN_AOV.md

**Documento Principal de Resultados**

Contiene:

- ✅ Resumen ejecutivo del análisis
- ✅ Estadísticas descriptivas del AOV
- ✅ Metodología y feature engineering
- ✅ Resultados de dos modelos (Regresión y Clasificación)
- ✅ Feature importance y factores clave
- ✅ Segmentación de clientes por AOV
- ✅ 6 recomendaciones estratégicas detalladas
- ✅ Proyección de impacto (hasta +30% en AOV)
- ✅ Casos de uso del modelo predictivo
- ✅ Limitaciones y próximos pasos

**📖 Léelo aquí**: [RESUMEN_AOV.md](./RESUMEN_AOV.md)

---

## 🎯 Highlights del Análisis

### Modelos Desarrollados

#### Modelo de Regresión

- **Objetivo**: Predecir valor exacto del ticket
- **Performance**: R² = 0.887, MAE = $2.89
- **Interpretación**: Explica 88.7% de la varianza

#### Modelo de Clasificación

- **Objetivo**: Clasificar tickets como Alto/Bajo
- **Performance**: ROC-AUC = 0.945, Accuracy = 88.7%
- **Interpretación**: 9 de cada 10 predicciones correctas

### Top 5 Factores Más Importantes

1. 🛒 **Total de Artículos** (28-31% de importancia)
2. 👤 **Ticket Promedio Histórico del Cliente** (18-19%)
3. 🏪 **Ticket Promedio de la Tienda** (13-14%)
4. ⭐ **Segmento Premium** (8-9%)
5. 📊 **Número de Transacciones del Cliente** (5-7%)

### Impacto Proyectado

| Escenario       | AOV Actual | AOV Proyectado | Mejora | Impacto Anual |
| --------------- | ---------- | -------------- | ------ | ------------- |
| **Conservador** | $19.87     | $22.45         | +13%   | **+$309,600** |
| **Optimista**   | $19.87     | $25.82         | +30%   | **+$714,000** |

---

## 🚀 Recomendaciones Clave

### 1. Cross-Selling y Bundling

- Aumentar artículos por transacción
- **Impacto**: +15% en AOV (+$3.00)

### 2. Personalización por Segmento

- Ofertas diferenciadas Premium/Regular/Budget
- **Impacto**: +10% en AOV (+$2.00)

### 3. Optimización de Promociones

- Priorizar 2x1 y monto fijo sobre porcentaje
- **Impacto**: +8% en AOV (+$1.60)

### 4. Gestión por Tienda

- Replicar mejores prácticas de tiendas top
- **Impacto**: +12% en AOV (+$2.40)

### 5. Timing y Contextualización

- Ofertas según horario, día y tráfico
- **Impacto**: +7% en AOV (+$1.40)

### 6. Programa de Lealtad

- Sistema escalonado Budget/Regular/Premium
- **Impacto**: +18% en AOV (+$3.60) largo plazo

---

## 📊 Datos del Análisis

### Período

- Enero - Marzo 2024 (3 meses)

### Volumen

- 10,000 transacciones analizadas
- 1,000 clientes únicos
- 10 tiendas

### Features

- 40+ features creadas
- 5 categorías: Temporales, Cliente, Tienda, Exógenas, Promocionales

### División de Datos

- Train: 70% (7,000 transacciones)
- Test: 15% (1,500 transacciones)
- Validation: 15% (1,500 transacciones)
- **Método**: Split estratificado

---

## 🔧 Archivos Técnicos Relacionados

### Código Fuente

- **Notebook Principal**: `../caso_c.ipynb`
- **Model Manager**: `../../src/model_manager.py`
- **Pipeline Manager**: `../../src/pipeline_manager.py`

### Datos

- **Transacciones**: `../../data/03_aov_drivers/transacciones_resumen.csv`
- **Clientes**: `../../data/03_aov_drivers/clientes_loyalty.csv`
- **Promociones**: `../../data/03_aov_drivers/promociones_activas.csv`
- **Variables Exógenas**: `../../data/03_aov_drivers/variables_exogenas.csv`

---

## 🎓 Casos de Uso del Modelo

### 1. Targeting de Clientes

Identificar clientes con alta probabilidad de ticket alto para enviar ofertas personalizadas.

### 2. Predicción de Ingresos

Estimar ingresos diarios por tienda para ajustar inventario y personal.

### 3. Optimización de Promociones

Evaluar impacto de promociones antes de lanzar para maximizar ROI.

---

## 📈 Próximos Pasos

### Corto Plazo (1-2 meses)

- ✅ Implementar cross-selling y optimización de promociones
- ✅ Piloto en 3 tiendas
- ✅ Dashboard de monitoreo
- ⏳ Entrenar personal

### Mediano Plazo (3-6 meses)

- ⏳ Expandir a todas las tiendas
- ⏳ Programa de lealtad
- ⏳ Integración en sistema POS
- ⏳ A/B testing

### Largo Plazo (6-12 meses)

- ⏳ Reentrenar con 12 meses de datos
- ⏳ Modelo de propensión por categoría
- ⏳ Pricing dinámico
- ⏳ Customer Lifetime Value

---

## 📞 Contacto

Para consultas sobre este análisis:

- **Email**: ds-team@tostao.com
- **Documentación**: Notebook `caso_c.ipynb`

---

## 📝 Versión

**v1.0** - Enero 2026

- Análisis completo de AOV drivers
- Dos modelos predictivos (Regresión + Clasificación)
- 6 recomendaciones estratégicas
- Proyección de impacto económico

---

_Análisis generado como parte de la Prueba Técnica - Data Science & ML - Tostao_
