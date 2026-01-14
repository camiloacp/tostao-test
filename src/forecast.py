from dataclasses import dataclass
import pandas as pd
import numpy as np
from typing import Tuple, List, Optional

import matplotlib.pyplot as plt
from scipy import stats

from prophet import Prophet


@dataclass(frozen=True)
class ForecastResult:
    id_tienda: str
    id_producto: str
    mu_semana: float
    sigma_semana: float
    last_date: pd.Timestamp


class DemandForecaster:
    """
    Pronóstico con Prophet:
    - Ajusta un modelo Prophet por (id_tienda, id_producto) sobre datos diarios
    - Predice n_days_ahead días
    - Agrega a semana sumando la media diaria (yhat)
    - Incertidumbre semanal aproximada:
        sigma_day ≈ (yhat_upper - yhat_lower) / (2*z)
        sigma_week ≈ sqrt(sum sigma_day^2)  (asumiendo independencia aproximada)
    """

    def __init__(
        self,
        min_history_days: int = 30,
        interval_width: float = 0.95,
        daily_seasonality: bool = False,
        weekly_seasonality: bool = True,
        yearly_seasonality: bool = False,
        seasonality_mode: str = "additive",
        changepoint_prior_scale: float = 0.05,
    ):
        self.min_history_days = min_history_days
        self.interval_width = interval_width
        self.daily_seasonality = daily_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.yearly_seasonality = yearly_seasonality
        self.seasonality_mode = seasonality_mode
        self.changepoint_prior_scale = changepoint_prior_scale

    def _make_model(self) -> Prophet:
        return Prophet(
            interval_width=self.interval_width,
            daily_seasonality=self.daily_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            yearly_seasonality=self.yearly_seasonality,
            seasonality_mode=self.seasonality_mode,
            changepoint_prior_scale=self.changepoint_prior_scale,
        )

    def fit_predict_week(self, sales_panel: pd.DataFrame, horizon_days: int = 7) -> pd.DataFrame:
        df = sales_panel.copy()
        df["id_tienda"] = df["id_tienda"].astype(str)
        df["id_producto"] = df["id_producto"].astype(str)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["unidades_vendidas"] = pd.to_numeric(df["unidades_vendidas"], errors="coerce").fillna(0.0)

        last_date_global = df["fecha"].max()

        out = []
        for (tienda, producto), g in df.groupby(["id_tienda", "id_producto"]):
            g = g.sort_values("fecha")

            # (1) Asegurar frecuencia diaria (relleno de faltantes con 0 o NaN según tu criterio)
            # Aquí uso 0.0 (común en demanda: no venta = 0). Si prefieres NaN, cámbialo.
            idx = pd.date_range(g["fecha"].min(), g["fecha"].max(), freq="D")
            g2 = g.set_index("fecha").reindex(idx)
            g2.index.name = "fecha"
            g2["unidades_vendidas"] = g2["unidades_vendidas"].fillna(0.0)

            y = g2["unidades_vendidas"].to_numpy()
            last_date = g2.index.max()

            # (2) Fallback si hay poco historial
            if len(y) < self.min_history_days:
                mu_d = float(np.mean(y)) if len(y) else 0.0
                sigma_d = float(np.std(y)) if len(y) else 0.0
                mu_w = max(0.0, horizon_days * mu_d)
                sigma_w = max(1.0, np.sqrt(horizon_days) * max(sigma_d, 1.0))
                forecast_end_date = last_date + pd.Timedelta(days=horizon_days)
                out.append(
                    ForecastResult(tienda, producto, mu_w, sigma_w, forecast_end_date)
                )
                continue

            # (3) Prophet requiere columnas ds, y
            train = g2.reset_index().rename(columns={"fecha": "ds", "unidades_vendidas": "y"})

            m = self._make_model()
            try:
                m.fit(train)
            except Exception:
                # fallback robusto si Prophet falla por alguna razón
                mu_d = float(np.mean(y))
                sigma_d = float(np.std(y))
                mu_w = max(0.0, horizon_days * mu_d)
                sigma_w = max(1.0, np.sqrt(horizon_days) * max(sigma_d, 1.0))
                forecast_end_date = last_date + pd.Timedelta(days=horizon_days)
                out.append(
                    ForecastResult(tienda, producto, mu_w, sigma_w, forecast_end_date)
                )
                continue

            # (4) Predecir horizonte diario
            future = m.make_future_dataframe(periods=horizon_days, freq="D", include_history=False)
            fcst = m.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

            # (5) Media semanal = suma de yhat (diario)
            mu_w = float(np.maximum(0.0, fcst["yhat"]).sum())

            # (6) Sigma semanal aproximada usando el ancho del intervalo (asumiendo Normal aprox)
            z = stats.norm.ppf((1.0 + self.interval_width) / 2.0)
            sigma_day = (fcst["yhat_upper"] - fcst["yhat_lower"]) / (2.0 * z)
            sigma_day = sigma_day.clip(lower=1e-6)  # evitar ceros numéricos
            sigma_w = float(np.sqrt(np.sum(np.square(sigma_day))))
            sigma_w = max(1.0, sigma_w)

            # Calcular la fecha final del pronóstico
            forecast_end_date = last_date + pd.Timedelta(days=horizon_days)

            out.append(
                ForecastResult(
                    id_tienda=tienda,
                    id_producto=producto,
                    mu_semana=mu_w,
                    sigma_semana=sigma_w,
                    last_date=forecast_end_date,
                )
            )

        return pd.DataFrame([r.__dict__ for r in out])
    
    def plot_time_series(
        self,
        sales_panel: pd.DataFrame,
        id_tienda: str,
        id_producto: str,
        figsize: Tuple[int, int] = (14, 6),
        show_prophet_fit: bool = True,
        show_interval: bool = True,
    ) -> plt.Figure:
        """
        Grafica la serie histórica (diaria) y, opcionalmente, el ajuste in-sample de Prophet
        (yhat) con su intervalo de incertidumbre.

        Nota: esto NO es pronóstico futuro, es el "fit" sobre el histórico.
        """
        df = sales_panel.copy()
        df["id_tienda"] = df["id_tienda"].astype(str)
        df["id_producto"] = df["id_producto"].astype(str)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["unidades_vendidas"] = pd.to_numeric(df["unidades_vendidas"], errors="coerce").fillna(0.0)

        g = df[
            (df["id_tienda"] == id_tienda) &
            (df["id_producto"] == id_producto)
        ].copy().sort_values("fecha")

        if g.empty:
            raise ValueError(f"No hay datos para tienda={id_tienda}, producto={id_producto}")

        # Reindex diario para que Prophet tenga frecuencia regular
        idx = pd.date_range(g["fecha"].min(), g["fecha"].max(), freq="D")
        g2 = g.set_index("fecha").reindex(idx)
        g2.index.name = "fecha"
        g2["unidades_vendidas"] = g2["unidades_vendidas"].fillna(0.0)

        fig, ax = plt.subplots(figsize=figsize)

        # Serie histórica
        ax.plot(
            g2.index,
            g2["unidades_vendidas"].values,
            label="Ventas Históricas (Diarias)",
            alpha=0.75,
            color="steelblue",
        )

        # Ajuste Prophet (in-sample)
        if show_prophet_fit:
            if len(g2) < self.min_history_days:
                # Fallback simple si no alcanza historial
                mu = float(g2["unidades_vendidas"].mean()) if len(g2) else 0.0
                ax.hlines(
                    mu,
                    xmin=g2.index.min(),
                    xmax=g2.index.max(),
                    colors="orangered",
                    linestyles="--",
                    linewidth=2,
                    label=f"Media histórica (fallback) = {mu:.1f}",
                )
            else:
                train = g2.reset_index().rename(columns={"fecha": "ds", "unidades_vendidas": "y"})
                m = self._make_model()
                m.fit(train)

                # Predicción sobre el mismo histórico (in-sample)
                fcst_hist = m.predict(train[["ds"]])[["ds", "yhat", "yhat_lower", "yhat_upper"]]

                ax.plot(
                    fcst_hist["ds"],
                    fcst_hist["yhat"],
                    label="Prophet fit (yhat)",
                    linewidth=2,
                    color="orangered",
                    linestyle="--",
                )

                if show_interval:
                    ax.fill_between(
                        fcst_hist["ds"].to_numpy(),
                        fcst_hist["yhat_lower"].to_numpy(),
                        fcst_hist["yhat_upper"].to_numpy(),
                        alpha=0.20,
                        color="orangered",
                        label=f"IC {int(self.interval_width*100)}% (fit)",
                        edgecolor="none",
                    )

        ax.set_xlabel("Fecha", fontsize=12)
        ax.set_ylabel("Unidades Vendidas", fontsize=12)
        ax.set_title(
            f"Serie Temporal (Histórico)\nTienda: {id_tienda}, Producto: {id_producto}",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        return fig

    def plot_forecast_with_intervals(
        self,
        sales_panel: pd.DataFrame,
        id_tienda: str,
        id_producto: str,
        horizon_days: int = 28,
        figsize: Tuple[int, int] = (14, 7),
    ) -> plt.Figure:
        df = sales_panel.copy()
        df["id_tienda"] = df["id_tienda"].astype(str)
        df["id_producto"] = df["id_producto"].astype(str)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["unidades_vendidas"] = pd.to_numeric(df["unidades_vendidas"], errors="coerce").fillna(0.0)

        g = df[(df["id_tienda"] == id_tienda) & (df["id_producto"] == id_producto)].copy()
        g = g.sort_values("fecha")

        if g.empty:
            raise ValueError("No hay datos para esa combinación tienda/producto")

        # daily reindex
        idx = pd.date_range(g["fecha"].min(), g["fecha"].max(), freq="D")
        g2 = g.set_index("fecha").reindex(idx)
        g2.index.name = "fecha"
        g2["unidades_vendidas"] = g2["unidades_vendidas"].fillna(0.0)

        train = g2.reset_index().rename(columns={"fecha": "ds", "unidades_vendidas": "y"})

        m = self._make_model()
        m.fit(train)

        future = m.make_future_dataframe(periods=horizon_days, freq="D", include_history=True)
        fcst = m.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(train["ds"], train["y"], label="Histórico", color="steelblue", alpha=0.7)
        ax.plot(fcst["ds"], fcst["yhat"], label="Prophet yhat", color="orangered", linewidth=2)

        ax.fill_between(
            fcst["ds"].to_numpy(),
            fcst["yhat_lower"].to_numpy(),
            fcst["yhat_upper"].to_numpy(),
            color="orangered",
            alpha=0.2,
            label=f"IC {int(self.interval_width*100)}%",
        )

        ax.axvline(train["ds"].max(), color="gray", linestyle=":", linewidth=2, label="Última fecha histórica")
        ax.set_title(f"Prophet Forecast - Tienda {id_tienda}, Producto {id_producto}")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Unidades vendidas")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        plt.xticks(rotation=45)
        plt.tight_layout()
        return fig
    
    def plot_multiple_series(
        self,
        sales_panel: pd.DataFrame,
        combinations: List[Tuple[str, str]],
        metric: str = "unidades_vendidas",
        resample_freq: Optional[str] = "W",
        figsize: Tuple[int, int] = (14, 8),
        show_prophet_fit: bool = True,
        show_interval: bool = False,
        max_combinations_fit: Optional[int] = 12,
    ) -> plt.Figure:
        """
        Grafica múltiples series temporales (históricas) y opcionalmente el ajuste in-sample de Prophet
        para cada combinación (tienda, producto).

        Parámetros clave:
        - show_prophet_fit: dibuja la curva yhat (fit) por combinación
        - show_interval: dibuja banda (yhat_lower, yhat_upper). Suele ensuciar el gráfico si hay muchas series
        - max_combinations_fit: limita cuántas combinaciones ajustan Prophet (por performance/claridad).
          Si None, ajusta todas.

        Nota:
        - Prophet se ajusta sobre datos diarios (reindex D). Si resample_freq != None, el histórico se agrega
          para visualización, pero el fit Prophet sigue siendo diario (y luego se agrega igual).
        """
        df = sales_panel.copy()
        df["id_tienda"] = df["id_tienda"].astype(str)
        df["id_producto"] = df["id_producto"].astype(str)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0.0)

        fig, ax = plt.subplots(figsize=figsize)

        # Paleta consistente
        palette = plt.cm.tab20(np.linspace(0, 1, max(1, len(combinations))))

        for i, (tienda, producto) in enumerate(combinations):
            g = df[
                (df["id_tienda"] == tienda) &
                (df["id_producto"] == producto)
            ].copy().sort_values("fecha")

            if g.empty:
                continue

            color = palette[i % len(palette)]

            # --- Histórico (para plot): opcionalmente agregado ---
            g_hist = g.set_index("fecha")[[metric]].sort_index()

            if resample_freq:
                hist_series = g_hist[metric].resample(resample_freq).sum()
            else:
                hist_series = g_hist[metric]

            ax.plot(
                hist_series.index,
                hist_series.values,
                label=f"Hist {tienda}-{producto}",
                linewidth=1.5,
                alpha=0.75,
                color=color,
                marker="o" if resample_freq else None,
                markersize=3,
            )

            # --- Prophet fit (in-sample), opcional ---
            if show_prophet_fit:
                if (max_combinations_fit is not None) and (i >= max_combinations_fit):
                    continue

                # Reindex diario para Prophet
                idx = pd.date_range(g["fecha"].min(), g["fecha"].max(), freq="D")
                g2 = g.set_index("fecha").reindex(idx)
                g2.index.name = "fecha"
                g2[metric] = g2[metric].fillna(0.0)

                if len(g2) < self.min_history_days:
                    # Fallback simple si hay poco historial
                    mu = float(g2[metric].mean()) if len(g2) else 0.0
                    # Pintamos una línea horizontal (en la escala agregada, esto es aproximado)
                    ax.hlines(
                        mu if not resample_freq else mu * (7 if resample_freq.startswith("W") else 1),
                        xmin=hist_series.index.min(),
                        xmax=hist_series.index.max(),
                        colors=[color],
                        linestyles="--",
                        linewidth=1.5,
                        alpha=0.9,
                    )
                    continue

                train = g2.reset_index().rename(columns={"fecha": "ds", metric: "y"})

                m = self._make_model()
                try:
                    m.fit(train)
                except Exception:
                    # Si falla, omitimos fit para esa serie
                    continue

                fcst_hist = m.predict(train[["ds"]])[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
                fcst_hist = fcst_hist.set_index("ds")

                # Si el gráfico está agregado, agregamos también el fit
                if resample_freq:
                    fit = fcst_hist["yhat"].resample(resample_freq).sum()
                    lower = fcst_hist["yhat_lower"].resample(resample_freq).sum()
                    upper = fcst_hist["yhat_upper"].resample(resample_freq).sum()
                else:
                    fit = fcst_hist["yhat"]
                    lower = fcst_hist["yhat_lower"]
                    upper = fcst_hist["yhat_upper"]

                ax.plot(
                    fit.index,
                    fit.values,
                    label=f"Fit {tienda}-{producto}",
                    linewidth=2.0,
                    alpha=0.9,
                    color=color,
                    linestyle="--",
                )

                if show_interval:
                    ax.fill_between(
                        fit.index.to_numpy(),
                        lower.to_numpy(),
                        upper.to_numpy(),
                        color=color,
                        alpha=0.10,
                        edgecolor="none",
                    )

        ax.set_xlabel("Fecha", fontsize=12)
        ylabel = metric.replace("_", " ").title()
        if resample_freq:
            ylabel += f" ({resample_freq})"
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title("Comparación de Series (Histórico + Fit Prophet)", fontsize=14, fontweight="bold")

        # Si hay demasiadas series, la leyenda puede ser inmanejable
        ax.legend(loc="best", fontsize=9, ncol=2)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        return fig