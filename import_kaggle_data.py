import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import logging

try:
    from ecommerce_price_prediction import Product, PriceHistory, Base
except ImportError:
    print("Run this from the ecommerce_price_monitoring directory")
    exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ecommerce_prices.db")
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

def simulate_kaggle_dataset(output_file="kaggle_retail_dataset_mock.csv"):
    """
    Génère un faux CSV ressemblant à un extrait de dataset Kaggle Retail
    """
    logger.info("Generating Kaggle-like dataset...")
    
    products_data = [
        {"product_id": 101, "name": "Wireless Noise-Cancelling Headphones", "category": "Electronics", "base_price": 250.0},
        {"product_id": 102, "name": "Mechanical Gaming Keyboard RGB", "category": "Electronics", "base_price": 120.0},
        {"product_id": 103, "name": "Smart Watch Series 7", "category": "Electronics", "base_price": 300.0},
    ]
    
    rows = []
    start_date = datetime.utcnow() - timedelta(days=120) # 4 month history
    
    for pd_data in products_data:
        current_price = pd_data["base_price"]
        for day in range(120):
            date = start_date + timedelta(days=day)
            
            # Simulate real market dynamics
            is_promo = np.random.rand() > 0.90
            price_noise = np.random.normal(0, 1.5)
            
            final_price = current_price + price_noise
            if is_promo:
                final_price *= np.random.uniform(0.70, 0.85) # 15 to 30% off
            
            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "product_name": pd_data["name"],
                "category": pd_data["category"],
                "price": round(final_price, 2),
                "is_discounted": int(is_promo)
            })
            
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    logger.info(f"Dataset generated and saved to {output_file} ({len(df)} rows)")
    return output_file

def import_to_sqlite(csv_file):
    logger.info("Importing dataset into SQLite via SQLAlchemy...")
    df = pd.read_csv(csv_file)
    
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    for _, row in df.iterrows():
        # Get or create product
        product = db.query(Product).filter(Product.name == row["product_name"]).first()
        if not product:
            product = Product(
                name=row["product_name"],
                url=f"http://kaggle-import/{row['product_name'].replace(' ', '-')}",
                category=row["category"]
            )
            db.add(product)
            db.commit()
            db.refresh(product)
            
        # Add price history
        history = PriceHistory(
            product_id=product.id,
            timestamp=datetime.strptime(row["date"], "%Y-%m-%d"),
            price=row["price"],
            discount_active=bool(row["is_discounted"])
        )
        db.add(history)
        
    db.commit()
    db.close()
    logger.info("Kaggle data successfully ingested!")

if __name__ == "__main__":
    csv_path = simulate_kaggle_dataset()
    import_to_sqlite(csv_path)
    logger.info("Run api_predictions.py to see this data live.")
