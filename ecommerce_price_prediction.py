import os
import time
import asyncio
import aiohttp
import sys
import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup

# Fix for Windows asyncio loop closure issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- SQLAlchemy ---
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# --- Macine Learning (XGBoost) ---
import xgboost as xgb
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import TimeSeriesSplit

# Logging config
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# =====================================================================
# 1. DATABASE & MODELS (Time-Series)
# =====================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ecommerce_prices.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    """Table referentiel des produits"""
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String, unique=True, index=True)
    category = Column(String)
    image_url = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False)
    is_trained = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

class PriceHistory(Base):
    """Table de Time-Series pour stocker l'historique."""
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    price = Column(Float)
    in_stock = Column(Boolean, default=True)
    discount_active = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# =====================================================================
# 2. DATA COLLECTOR (ASYNC SCRAPER & SIMULATOR)
# =====================================================================
class DataCollector:
    """Gere l'extraction de donnee asynchrone pour N produits."""
    
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async def fetch_page(self, session, url):
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

            # 4. Nouveau : Extraction d'image
            image_url = None
            og_image = soup.find('meta', property='og:image')
            if og_image:
                image_url = og_image['content']
            
            return {"price": None, "image_url": image_url}
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return {"price": None, "image_url": None}

    def extract_data_from_html(self, html_content: str):
        """Parse le prix ET l'image depuis le code HTML."""
        if not html_content: return {"price": None, "image_url": None}
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Tentative Shopify / ColourPop
            price = None
            price_sale = soup.select_one('.price-item--sale')
            if price_sale:
                price = float(re.sub(r'[^\d.]', '', price_sale.text.strip()))
            else:
                price_reg = soup.select_one('.price-item--regular')
                if price_reg:
                    price = float(re.sub(r'[^\d.]', '', price_reg.text.strip()))

            # 2. Sélecteurs génériques schema.org
            if price is None:
                meta_price = soup.find('meta', property='og:price:amount')
                if meta_price:
                    price = float(meta_price['content'])

            # 3. Ancien sélecteur Books To Scrape
            if price is None:
                price_element = soup.select_one('.price_color')
                if price_element:
                    price_str = price_element.text.replace('£', '').replace('€', '').strip()
                    price = float(price_str)
            
            # 4. Extraction d'image améliorée
            image_url = None
            
            # Priorité 1: Open Graph (Standard)
            og_image = soup.find('meta', property='og:image') or soup.find('meta', property='twitter:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
            
            # Priorité 2: Shopify Common Media
            if not image_url:
                img_tag = soup.select_one('.product__media img, .product-single__media img, .product-main-image img')
                if img_tag and img_tag.get('src'):
                    image_url = img_tag['src']

            # Priorité 3: Première grande image
            if not image_url:
                for img in soup.find_all('img', src=True):
                    if any(x in img['src'].lower() for x in ['product', 'products', 'upload']):
                        image_url = img['src']
                        break
            
            # Nettoyage et conversion en URL absolue
            if image_url:
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    # Tentative de reconstruction si URL relative (basique)
                    image_url = "https://colourpop.com" + image_url # Fallback spécifique si domaine inconnu
            
            return {"price": price, "image_url": image_url}
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return {"price": None, "image_url": None}

    async def bootstrap_real_products(self, db):
        """Scrape une vraie liste de produits Initiale (Catalogue) depuis l'API ColourPop."""
        logger.info("Bootstrapping real products from ColourPop Cosmetics API...")
        base_url = "https://colourpop.com/products.json?limit=15"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(base_url, headers=self.headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get('products', []):
                            name = item.get('title')
                            handle = item.get('handle')
                            full_url = f"https://colourpop.com/products/{handle}"
                            price_str = item.get('variants', [{}])[0].get('price', "20.00")
                            try:
                                initial_price = float(price_str)
                            except:
                                initial_price = 20.0
                                
                            category = item.get('product_type', 'Cosmetics')
                            img_url = item.get('images', [{}])[0].get('src')
                            p = Product(name=name, url=full_url, category=category, image_url=img_url)
                            db.add(p)
                            db.commit()
                            db.refresh(p)
                            generate_initial_history_for_product(db, p.id, base_price=initial_price)
            except Exception as e:
                logger.error(f"Failed to bootstrap API: {e}")

    async def run_scraping_cycle(self):
        logger.info("Starting true async scraping cycle...")
        db = SessionLocal()
        products = db.query(Product).filter(Product.active == True).all()
        
        # Generation des produits à partir d'un vrai site si base vide
        if not products:
            await self.bootstrap_real_products(db)
            products = db.query(Product).all()

        if not products:
            logger.error("Failed to bootstrap products.")
            db.close()
            return


        async with aiohttp.ClientSession() as session:
            for product in products:
                real_price = None
                is_discount = False
                
                # OPTIMISATION COLORPOP : Utilisation de l'API JSON Shopify (.js)
                if "colourpop.com" in product.url:
                    json_url = product.url + ".js"
                    try:
                        async with session.get(json_url, headers=self.headers, timeout=5) as resp:
                            if resp.status == 200:
                                data = await resp.json(content_type=None)
                                # Price est en centimes chez Shopify
                                real_price = float(data.get('price')) / 100.0
                                # Détection de promo réelle
                                compare_at = data.get('compare_at_price')
                                if compare_at and float(compare_at) > float(data.get('price')):
                                    is_discount = True
                    except Exception as e:
                        logger.warning(f"JSON API failed for {product.url}: {e}")

                # BACKUP : Scraping HTML classique si JSON échoue ou site tiers
                if real_price is None:
                    html = await self.fetch_page(session, product.url)
                    data = self.extract_data_from_html(html)
                    real_price = data["price"]
                    if not product.image_url and data["image_url"]:
                        product.image_url = data["image_url"]

                # Si on a un prix, on l'enregistre SANS BRUIT (Real data only)
                if real_price is not None:
                    final_price = round(real_price, 2)
                    hist = PriceHistory(
                        product_id=product.id, 
                        price=final_price, 
                        discount_active=is_discount
                    )
                    db.add(hist)
                    logger.info(f"Updated {product.name}: {final_price} (Real Price)")
                else:
                    logger.warning(f"Could not update price for {product.name}")
        
        db.commit()
        db.close()
        logger.info("Scraping cycle complete. Real prices used.")

# =====================================================================
# 3. FEATURE ENGINEERING
# =====================================================================
class FeatureEngineer:
    """Genere au moins 15 features ML a partir d'une serie temporelle univariée."""
    
    @staticmethod
    def generate_features(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        df = df.sort_values(by="timestamp").copy()
        
        # Features Temporelles (1-5)
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['month'] = df['timestamp'].dt.month
        df['day_of_month'] = df['timestamp'].dt.day
        # Encodage sin/cos (cyclique)
        df['sin_day'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        
        # Lags: prix prededent (6-8)
        df['price_lag_1'] = df['price'].shift(1)
        df['price_lag_3'] = df['price'].shift(3)
        df['price_lag_7'] = df['price'].shift(7)
        
        # Rolling stats (9-12)
        df['price_rolling_mean_3d'] = df['price'].rolling(window=3).mean()
        df['price_rolling_mean_7d'] = df['price'].rolling(window=7).mean()
        df['price_rolling_std_7d'] = df['price'].rolling(window=7).std().fillna(0)
        df['price_rolling_max_7d'] = df['price'].rolling(window=7).max()
        
        # Momentum & Ratios (13-15+)
        df['price_momentum'] = (df['price'] - df['price_lag_3']) / (df['price_lag_3'] + 1e-5)
        df['discount_ratio'] = df['price'] / (df['price_rolling_max_7d'] + 1e-5)
        df['consecutive_discounts'] = df['discount_active'].rolling(window=3).sum()

        # Handle NaNs for short history instead of dropping all rows
        df = df.bfill().ffill().fillna(0)
        return df

# =====================================================================
# 4. MACHINE LEARNING: PRICE PREDICTOR
# =====================================================================
class PricePredictor:
    """Gere l'entrainement de XGBoost et les prédictions futures."""
    
    def __init__(self):
        self.model = xgb.XGBRegressor(
            n_estimators=100, learning_rate=0.05, max_depth=5, 
            objective='reg:squarederror'
        )
        self.features_col = [
            'day_of_week', 'is_weekend', 'month', 'sin_day',
            'price_lag_1', 'price_rolling_mean_3d', 'price_rolling_mean_7d',
            'price_rolling_std_7d', 'price_momentum', 'discount_ratio'
        ]
        
    def fetch_data(self, product_id: int):
        db = SessionLocal()
        data = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).all()
        db.close()
        df = pd.DataFrame([{
            'timestamp': d.timestamp,
            'price': d.price,
            'discount_active': 1 if d.discount_active else 0
        } for d in data])
        return df

    def train_model(self, product_id: int):
        logger.info(f"Training XGBoost for Product {product_id}...")
        df = self.fetch_data(product_id)
        if len(df) < 20:
             logger.warning("Not enough data to train.")
             return False

        df = FeatureEngineer.generate_features(df)
        
        # Creation de la target : y_target est le prix de DEMAIN (shift -1)
        df['target'] = df['price'].shift(-1)
        df = df.dropna()

        X = df[self.features_col]
        y = df['target']
        
        if len(X) < 5: return False

        # Modele entrainé sur 
        # tout le dataset 
        self.model.fit(X, y)
        
        # Validation sur TimeSeriesSplit pour la metrique MAPE
        tscv = TimeSeriesSplit(n_splits=3)
        mapes = []
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            m = xgb.XGBRegressor(n_estimators=50).fit(X_train, y_train)
            preds = m.predict(X_test)
            mapes.append(mean_absolute_percentage_error(y_test, preds))
            
        logger.info(f"Product {product_id} Trained. CV MAPE: {np.mean(mapes):.4f}")
        return True

    def predict_next_7_days(self, product_id: int):
        """Genere recursivement les prix pour les 7 prochains jours."""
        df = self.fetch_data(product_id)
        if len(df) < 5: return []
        
        df = FeatureEngineer.generate_features(df)
        if df.empty: return []
        last_row = df.iloc[-1:].copy()
        
        predictions = []
        current_date = last_row['timestamp'].values[0]
        
        for i in range(1, 8):
            X = last_row[self.features_col]
            pred_price = self.model.predict(X)[0]
            
            next_date = pd.to_datetime(current_date) + timedelta(days=1)
            predictions.append({"date": next_date.strftime("%Y-%m-%d"), "predicted_price": float(round(pred_price, 2))})
            
            # Mise à jour recuscritive simplifiée (On devrait idéalement re-passer FeatureEngineer)
            last_row['price_lag_1'] = pred_price
            current_date = next_date
            
        return predictions

# =====================================================================
# 5. GENERATEUR HISTORIQUE BOOTSTRAP (Demarrage rapide)
# =====================================================================
def generate_initial_history_for_product(db, product_id: int, base_price: float = None):
    import random
    if base_price is None:
        base_price = 50.0 + np.random.uniform(-10, 50)
    
    # Check if history already exists
    count = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).count()
    if count > 0: return

    now = datetime.utcnow()
    for days_ago in range(90, -1, -1):
        timestamp = now - timedelta(days=days_ago)
        noise = np.random.normal(0, base_price * 0.05)
        price = base_price + noise
        
        is_discount = False
        if (days_ago % 20) < 4:
            price *= random.uniform(0.75, 0.85)
            is_discount = True
            
        db.add(PriceHistory(product_id=product_id, timestamp=timestamp, price=round(max(1.0, price), 2), discount_active=is_discount))
    db.commit()

def generate_historical_data_if_empty():
    db = SessionLocal()
    products = db.query(Product).all()
    if not products:
        db.close()
        return
        
    for p in products: 
        generate_initial_history_for_product(db, p.id)
    db.close()

# =====================================================================
# 6. MAIN EXECUTION
# =====================================================================
if __name__ == "__main__":
    logger.info("=== Starting E-Commerce Price Prediction Core System ===")
    
    collector = DataCollector()
    asyncio.run(collector.run_scraping_cycle())
    
    # We generate historical data AFTER creating products
    generate_historical_data_if_empty()
    
    predictor = PricePredictor()
    predictor.train_model(product_id=1)
    preds = predictor.predict_next_7_days(product_id=1)
    logger.info(f"7-Day Projections for Product 1: {preds}")
    
    logger.info("System Ready. Run 'api_predictions.py' to serve these models.")
