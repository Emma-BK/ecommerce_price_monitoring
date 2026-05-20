# %% [markdown]
# # 📊 Notebook d'Analyse : E-commerce Time-Series 
# Ce notebook permet de visualiser la qualité des données de prix récoltées.
# Il est directement exécutable dans VS Code (Interactive Window) ou Jupyter.

# %%
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.figsize'] = (14, 6)

print("📚 Libraries DataScience chargées.")

# %% [markdown]
# ## 1. Extraction depuis la Base de Données
# Nous chargeons l'historique de SQLite vers un DataFrame Pandas.

# %%
# Connexion DB
DATABASE_PATH = "ecommerce_prices.db"
try:
    conn = sqlite3.connect(DATABASE_PATH)
    query = """
    SELECT p.name, ph.product_id, ph.timestamp, ph.price, ph.discount_active 
    FROM price_history ph
    JOIN products p ON p.id = ph.product_id
    """
    df = pd.read_sql_query(query, conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"✅ Chargé {len(df)} enregistrements avec succès.")
except Exception as e:
    print(f"❌ Erreur: Lancez d'abord ecommerce_price_prediction.py pour générer la DB. ({e})")

# %% [markdown]
# ## 2. Analyse Exploratoire : Historique des Prix par Produit

# %%
if 'df' in locals() and not df.empty:
    plt.figure(figsize=(15, 7))
    sns.lineplot(data=df, x='timestamp', y='price', hue='name', linewidth=2.5)
    plt.title("📉 Historique des prix d'appareils e-commerce (90 derniers jours)", fontsize=16)
    plt.ylabel("Prix (€/$)", fontsize=12)
    plt.xlabel("Date", fontsize=12)
    plt.legend(title="Produit", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

# %% [markdown]
# ## 3. Détection des Promotions (Impact sur le Prix)
# Les points rouges indiquent où un "discount" a été détecté par le scraper.

# %%
if 'df' in locals() and not df.empty:
    # On isole un produit pour mieux voir
    prod1 = df[df['product_id'] == 1].copy()
    
    plt.figure(figsize=(14, 6))
    
    # Ligne de prix
    sns.lineplot(data=prod1, x='timestamp', y='price', color="royalblue", label='Prix Standard')
    
    # Points de promotions
    discounts = prod1[prod1['discount_active'] == 1]
    plt.scatter(discounts['timestamp'], discounts['price'], color="red", s=100, zorder=5, label='Promotion (<20%)')
    
    plt.title(f"🏷️ Analyse des Promotions : {prod1['name'].iloc[0]}", fontsize=15)
    plt.legend()
    plt.show()

# %% [markdown]
# ## 4. Feature Correlation (Importance XGBoost)
# Regardons quelles matrices temporelles sont les plus corrélées entre elles.

# %%
if 'df' in locals() and not df.empty:
    # Reproduction simple des features de notre app
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['price_lag_1'] = df.groupby('product_id')['price'].shift(1)
    df['price_lag_7'] = df.groupby('product_id')['price'].shift(7)
    df['rolling_mean_7d'] = df.groupby('product_id')['price'].transform(lambda x: x.rolling(7).mean())
    df_clean = df.dropna()

    cols_to_corr = ['price', 'day_of_week', 'price_lag_1', 'price_lag_7', 'rolling_mean_7d']
    corr_matrix = df_clean[cols_to_corr].corr()

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", fmt=".2f", linewidths=.5)
    plt.title("🔥 Heatmap de Corrélation des Features Temporelles")
    plt.show()

# %% [markdown]
# **FIN DU RUN** 
# (En Production, ces graphiques pourraient être exposés sur un backend Streamlit ou Dash en complément de FastAPI).
