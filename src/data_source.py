from dataclasses import dataclass
import pandas as pd
from typing import Tuple

@dataclass(frozen=True)
class PipelineConfig:
    n_window: int = 8
    z_low: float = -1.2816   # p10 aprox normal
    z_high: float = 1.2816   # p90 aprox normal
    week_freq: str = 'W-MON'
    sigma_floor: float = 0.5
    fractil_clip: Tuple[float, float] = (0.01, 0.99)


@dataclass
class DataSource:
    ventas_path: str = '../data/01_supply_optimization/ventas_historicas.csv'
    inventario_path: str = '../data/01_supply_optimization/inventario_actual.csv'
    catalogo_path: str = '../data/01_supply_optimization/catalogo_productos.csv'
    tiendas_path: str = '../data/01_supply_optimization/maestro_tiendas.csv'

    def load(self) -> "DataSource":
        self.ventas = pd.read_csv(self.ventas_path)
        self.inventario = pd.read_csv(self.inventario_path)
        self.catalogo = pd.read_csv(self.catalogo_path)
        self.tiendas = pd.read_csv(self.tiendas_path)
        return self

    def sales_daily(self) -> pd.DataFrame:
        v = self.ventas.copy()

        v["id_tienda"] = v["id_tienda"].astype(str)
        v["id_producto"] = v["id_producto"].astype(str)

        v["fecha"] = pd.to_datetime(v["fecha"])
        min_date, max_date = v["fecha"].min(), v["fecha"].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq="D")

        pairs = v[["id_tienda", "id_producto"]].drop_duplicates()
        idx = pairs.merge(pd.DataFrame({"fecha": all_dates}), how="cross")

        daily = (
            v.groupby(["id_tienda", "id_producto", "fecha"], as_index=False)["unidades_vendidas"]
            .sum()
        )

        panel = idx.merge(daily, on=["id_tienda", "id_producto", "fecha"], how="left")
        panel["unidades_vendidas"] = panel["unidades_vendidas"].fillna(0.0)
        return panel

    def master_store(self) -> pd.DataFrame:
        inv = self.inventario.copy()
        cat = self.catalogo.copy()
        tds = self.tiendas.copy()

        inv["id_tienda"] = inv["id_tienda"].astype(str)
        inv["id_producto"] = inv["id_producto"].astype(str)
        cat["id_producto"] = cat["id_producto"].astype(str)
        tds["id_tienda"] = tds["id_tienda"].astype(str)

        m = inv.merge(cat, on="id_producto", how="left").merge(tds, on="id_tienda", how="left")

        # Margen unitario: lo que se deja de ganar por unidad no vendida
        m["margen_unitario"] = (m["precio_venta"] - m["costo_unitario"]).clip(lower=0.0)
        # Costo de overstock: costo de mantener inventario por semana
        m["costo_overstock"] = (m["costo_unitario"] + m["costo_almacenamiento_semanal"]).clip(lower=0.0)

        return m