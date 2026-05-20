import warnings
warnings.filterwarnings("ignore")

import urllib.request
import re
import sys
import asyncio
from bs4 import BeautifulSoup
from fastapi import FastAPI, Depends, HTTPException, status

# Fix for Windows asyncio loop closure issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, text

# Import from core logic
from ecommerce_price_prediction import SessionLocal, Product, PriceHistory, PricePredictor, generate_initial_history_for_product

# =====================================================================
# 1. API INSTANCE & METAS
# =====================================================================
app = FastAPI(
    title="E-commerce Price Monitoring & Prediction API",
    description="API robuste pour ingérer des historiques de prix et prédire grâce à XGBoost.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Serve static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# =====================================================================
# 2. DEPENDENCY INJECTION (Database)
# =====================================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================================
# 3. PYDANTIC SCHEMAS (Validation des données in/out)
# =====================================================================
class ProductCreate(BaseModel):
    name: str
    url: HttpUrl
    category: Optional[str] = "General"

class ProductResponse(BaseModel):
    id: int
    name: str
    url: str
    category: Optional[str]
    image_url: Optional[str]
    is_favorite: bool
    active: bool

    class Config:
        from_attributes = True

class PriceRecordCreate(BaseModel):
    price: float
    discount_active: bool = False

class PriceRecordResponse(PriceRecordCreate):
    id: int
    product_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class PredictionResponse(BaseModel):
    date: str
    predicted_price: float

# =====================================================================
# 4. ENDPOINTS: SYSTEM HEALTH (2 endpoints)
# =====================================================================
from fastapi.responses import FileResponse

# =====================================================================
# 4. ENDPOINTS: SYSTEM HEALTH & FRONTEND
# =====================================================================
@app.get("/", tags=["UI"])
def serve_dashboard():
    """Sert l'interface graphique du Dashboard."""
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"message": f"Welcome to API. Frontend not found in {STATIC_DIR}."}

@app.get("/api/v1/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "timestamp": datetime.utcnow()}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database Service Unavailable")

# =====================================================================
# 5. ENDPOINTS: PRODUCTS (CRUD - 5 endpoints)
# =====================================================================
def scrape_real_price(url: str):
    try:
        # OPTIMISATION COLORPOP : JSON API
        if "colourpop.com" in url:
            json_url = url + ".js"
            req = urllib.request.Request(json_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    import json
                    data = json.loads(response.read().decode('utf-8'))
                    return float(data.get('price')) / 100.0

        # BACKUP : Scraping HTML
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                html = response.read().decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Shopify selectors
                price_sale = soup.select_one('.price-item--sale')
                if price_sale:
                    return float(re.sub(r'[^\d.]', '', price_sale.text.strip()))
                
                price_reg = soup.select_one('.price-item--regular')
                if price_reg:
                    return float(re.sub(r'[^\d.]', '', price_reg.text.strip()))

                # Generic Books To Scrape
                price_color = soup.select_one('.price_color')
                if price_color:
                    return float(price_color.text.replace('£', '').replace('€', '').strip())
                
                # Meta tags
                meta_price = soup.find('meta', property='og:price:amount')
                if meta_price:
                    return float(meta_price['content'])
    except Exception:
        pass
    return None

from ecommerce_price_prediction import DataCollector
collector = DataCollector()

@app.post("/api/v1/products/{product_id}/scrape", tags=["Products"])
async def trigger_manual_scrape(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Product not found")
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        html = await collector.fetch_page(session, prod.url)
        data = collector.extract_data_from_html(html)
        
        if data["price"]:
            hist = PriceHistory(product_id=prod.id, price=data["price"])
            db.add(hist)
            if data["image_url"]:
                prod.image_url = data["image_url"]
            db.commit()
            return {"status": "success", "new_price": data["price"]}
    
    return {"status": "failed", "detail": "Could not extract price"}

@app.post("/api/v1/products/{product_id}/favorite", tags=["Products"])
def toggle_favorite(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Product not found")
    prod.is_favorite = not prod.is_favorite
    db.commit()
    return {"status": "success", "is_favorite": prod.is_favorite}

@app.get("/api/v1/products/{product_id}/export", tags=["Products"])
def export_csv(product_id: int, db: Session = Depends(get_db)):
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Product not found")
    
    records = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).order_by(desc(PriceHistory.timestamp)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Price", "Discount Active"])
    for r in records:
        writer.writerow([r.timestamp, r.price, r.discount_active])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=history_product_{product_id}.csv"}
    )

@app.post("/api/v1/products", response_model=ProductResponse, tags=["Products"])
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_prod = db.query(Product).filter(Product.url == str(product.url)).first()
    if db_prod:
        raise HTTPException(status_code=400, detail="Product URL already registered")
    new_product = Product(name=product.name, url=str(product.url), category=product.category)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    # Scrape the real price as base_price for historical generation
    real_price = scrape_real_price(str(new_product.url))
    
    # Generate mock history immediately for testing XGBoost predictions
    generate_initial_history_for_product(db, new_product.id, real_price)
    
    return new_product

@app.get("/api/v1/products", response_model=List[ProductResponse], tags=["Products"])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.active == True).offset(skip).limit(limit).all()

@app.get("/api/v1/products/{product_id}", response_model=ProductResponse, tags=["Products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Product not found")
    return prod

@app.delete("/api/v1/products/{product_id}", tags=["Products"])
def disable_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Product not found")
    prod.active = False
    db.commit()
    return {"message": f"Product {product_id} disabled."}

# =====================================================================
# 6. ENDPOINTS: PRICE HISTORY (4 endpoints)
# =====================================================================
@app.post("/api/v1/products/{product_id}/prices", response_model=PriceRecordResponse, tags=["Prices"])
def add_price_record(product_id: int, price_data: PriceRecordCreate, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Product not found")
    
    record = PriceHistory(
        product_id=product_id, 
        price=price_data.price, 
        discount_active=price_data.discount_active
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.get("/api/v1/products/{product_id}/prices", response_model=List[PriceRecordResponse], tags=["Prices"])
def get_price_history(product_id: int, limit: int = 30, db: Session = Depends(get_db)):
    records = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)\
                .order_by(desc(PriceHistory.timestamp)).limit(limit).all()
    return records

@app.get("/api/v1/products/{product_id}/prices/latest", response_model=PriceRecordResponse, tags=["Prices"])
def get_latest_price(product_id: int, db: Session = Depends(get_db)):
    record = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)\
               .order_by(desc(PriceHistory.timestamp)).first()
    if not record: raise HTTPException(status_code=404, detail="No price records found")
    return record

# =====================================================================
# 7. ENDPOINTS: MACHINE LEARNING & PREDICTIONS (4 endpoints)
# =====================================================================
@app.post("/api/v1/predict/train/{product_id}", tags=["Machine Learning"])
def trigger_training(product_id: int, db: Session = Depends(get_db)):
    """Lance un entrainement XGBoost a part."""
    predictor = PricePredictor()
    success = predictor.train_model(product_id)
    if not success:
        raise HTTPException(status_code=400, detail="Not enough historical data to generate features for XGBoost.")
    
    # Mark as trained
    prod = db.query(Product).filter(Product.id == product_id).first()
    if prod:
        prod.is_trained = True
        db.commit()
        
    return {"message": f"Model for product {product_id} trained successfully."}

@app.get("/api/v1/predict/{product_id}", response_model=List[PredictionResponse], tags=["Machine Learning"])
def get_7_day_prediction(product_id: int):
    """Generates the 7 days ahead forecast."""
    predictor = PricePredictor()
    try:
        # On entraine on the fly pour l'exemple (en prod, un crontab le fera la nuit)
        predictor.train_model(product_id)
        predictions = predictor.predict_next_7_days(product_id)
        if not predictions:
            raise HTTPException(status_code=400, detail="Unable to predict line. Insufficient historical data.")
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/{product_id}/volatility", tags=["Analytics"])
def get_volatility(product_id: int, db: Session = Depends(get_db)):
    """Calcule la volatilité (ecart type) sur les 30 derniers jours."""
    records = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)\
                .order_by(desc(PriceHistory.timestamp)).limit(30).all()
    if len(records) < 2: return {"volatility": 0.0}
    prices = [r.price for r in records]
    
    import statistics
    volatility = statistics.stdev(prices)
    return {"product_id": product_id, "30_day_volatility": volatility, "currency": "EUR/USD"}

@app.get("/api/v1/analytics/categories", tags=["Analytics"])
def get_category_analytics(db: Session = Depends(get_db)):
    from sqlalchemy import func
    results = db.query(
        Product.category, 
        func.count(Product.id).label("count"),
        func.avg(PriceHistory.price).label("avg_price")
    ).join(PriceHistory, Product.id == PriceHistory.product_id)\
     .filter(Product.active == True)\
     .group_by(Product.category).all()
    
    return [{"category": r[0] or "General", "count": r[1], "avg_price": round(r[2], 2)} for r in results]

@app.get("/api/v1/analytics/global", tags=["Analytics"])
def get_global_analytics(db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    total_prods = db.query(Product).filter(Product.active == True).count()
    fav_prods = db.query(Product).filter(Product.active == True, Product.is_favorite == True).count()
    
    # Count manually trained models
    models_trained = db.query(Product).filter(Product.active == True, Product.is_trained == True).count()
        
    # Active discounts: latest price < 90% of avg price
    # This is a bit more complex in SQL, so we'll do a simpler check:
    # Products where any price in last 24h is 10% lower than their overall avg
    # For now, let's just keep the logic but make it more efficient if possible
    # Actually, looping over active products is fine if the count is small (<100)
    
    active_discounts = 0
    products = db.query(Product).filter(Product.active == True).all()
    for p in products:
        # Get avg and latest in one go
        stats = db.query(func.avg(PriceHistory.price), func.max(PriceHistory.timestamp))\
            .filter(PriceHistory.product_id == p.id).first()
            
        if stats and stats[0]:
            avg_price = stats[0]
            latest = db.query(PriceHistory.price).filter(PriceHistory.product_id == p.id)\
                .order_by(desc(PriceHistory.timestamp)).first()
            if latest and latest[0] < (avg_price * 0.9):
                active_discounts += 1

    return {
        "total_products": total_prods,
        "favorite_products": fav_prods,
        "active_discounts": active_discounts,
        "models_trained": models_trained,
        "last_update": datetime.utcnow()
    }

@app.get("/api/v1/alerts", tags=["Analytics"])
def get_alerts(db: Session = Depends(get_db)):
    # Find products where last price is 5% lower than 7-day average
    from sqlalchemy import func
    from datetime import timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    alerts = []
    products = db.query(Product).filter(Product.active == True).all()
    for p in products:
        latest = db.query(PriceHistory).filter(PriceHistory.product_id == p.id).order_by(desc(PriceHistory.timestamp)).first()
        if not latest: continue
        
        avg_price = db.query(func.avg(PriceHistory.price)).filter(
            PriceHistory.product_id == p.id,
            PriceHistory.timestamp >= seven_days_ago
        ).scalar() or latest.price
        
        if latest.price < (avg_price * 0.95):
            alerts.append({
                "product_id": p.id,
                "name": p.name,
                "price": latest.price,
                "old_avg": round(avg_price, 2),
                "drop_percent": round((avg_price - latest.price) / avg_price * 100, 1),
                "timestamp": latest.timestamp
            })
    
    return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)
