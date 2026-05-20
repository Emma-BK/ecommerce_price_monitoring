import asyncio
import aiohttp
from ecommerce_price_prediction import SessionLocal, Product, DataCollector

async def fix_missing_images():
    db = SessionLocal()
    collector = DataCollector()
    products = db.query(Product).filter(Product.image_url == None).all()
    print(f"Found {len(products)} products without images.")
    
    async with aiohttp.ClientSession() as session:
        for p in products:
            print(f"Scraping image for {p.name}...")
            html = await collector.fetch_page(session, p.url)
            data = collector.extract_data_from_html(html)
            if data["image_url"]:
                p.image_url = data["image_url"]
                print(f"  Success: {data['image_url']}")
            else:
                print(f"  Failed to find image.")
    
    db.commit()
    db.close()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(fix_missing_images())
