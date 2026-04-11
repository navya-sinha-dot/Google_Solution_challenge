#!/usr/bin/env python3
"""
Query all data from Neon PostgreSQL database.
Shows contents of all tables: weather_data, alerts, installations,
system_health, trends, user_preferences, users
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime

# Fix Windows console encoding for emoji
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

def query_all():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set in .env")
        return
    
    print(f"\n{'='*80}")
    print(f"🗄️  NEON POSTGRESQL DATABASE CONTENTS")
    print(f"{'='*80}")
    print(f"Host: {db_url.split('@')[-1].split('/')[0]}")
    print(f"Queried at: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    engine = create_engine(db_url, pool_pre_ping=True)
    
    with engine.connect() as conn:
        # ── 1. WEATHER DATA ──
        print(f"\n{'─'*80}")
        print(f"📊 TABLE: weather_data")
        print(f"{'─'*80}")
        
        count = conn.execute(text("SELECT COUNT(*) FROM weather_data")).fetchone()[0]
        print(f"   Total records: {count}")
        
        if count > 0:
            rows = conn.execute(text("""
                SELECT id, station_id, timestamp,
                       temperature, humidity, pressure,
                       wind_speed, wind_direction, rainfall,
                       soil_temperature, soil_moisture,
                       pm25, pm10, uv_index, lux,
                       battery_voltage, solar_voltage
                FROM weather_data 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)).fetchall()
            
            print(f"   Latest {len(rows)} records:\n")
            print(f"   {'ID':<5} {'Station':<8} {'Timestamp':<22} {'Temp°C':<8} {'Humid%':<8} {'Press':<10} {'Wind':<8} {'Dir':<6} {'Rain':<6} {'SoilT':<7} {'SoilM%':<7} {'PM2.5':<7} {'PM10':<7} {'UV':<5} {'Lux':<8} {'Bat V':<7} {'Sol V':<7}")
            print(f"   {'─'*140}")
            for row in rows:
                print(f"   {row[0]:<5} {str(row[1]):<8} {str(row[2]):<22} {row[3] or 0:<8.1f} {row[4] or 0:<8.1f} {row[5] or 0:<10.1f} {row[6] or 0:<8.1f} {str(row[7] or 'N'):<6} {row[8] or 0:<6.2f} {row[9] or 0:<7.1f} {row[10] or 0:<7.1f} {row[11] or 0:<7.1f} {row[12] or 0:<7.1f} {row[13] or 0:<5.1f} {row[14] or 0:<8.0f} {row[15] or 0:<7.2f} {row[16] or 0:<7.2f}")
        else:
            print("   ⚠️  No weather data yet. Run the bridge + MQTT simulator to start logging.")
        
        # ── 2. USERS ──
        print(f"\n{'─'*80}")
        print(f"👤 TABLE: users")
        print(f"{'─'*80}")
        
        count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
        print(f"   Total records: {count}")
        
        if count > 0:
            rows = conn.execute(text("SELECT phone, name, land_size_acres, location, crops, created_at FROM users LIMIT 10")).fetchall()
            for row in rows:
                print(f"   Phone: {row[0]}, Name: {row[1]}, Land: {row[2]} acres, Location: {row[3]}, Crops: {row[4]}")
        
        # ── 3. ALERTS ──
        print(f"\n{'─'*80}")
        print(f"🚨 TABLE: alerts")
        print(f"{'─'*80}")
        
        count = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]
        print(f"   Total records: {count}")
        
        if count > 0:
            rows = conn.execute(text("SELECT id, user_id, station_id, metric, operator, threshold, active FROM alerts LIMIT 10")).fetchall()
            for row in rows:
                print(f"   Alert #{row[0]}: user={row[1]}, station={row[2]}, {row[3]} {row[4]} {row[5]}, active={row[6]}")
        
        # ── 4. INSTALLATIONS ──
        print(f"\n{'─'*80}")
        print(f"📡 TABLE: installations")
        print(f"{'─'*80}")
        
        count = conn.execute(text("SELECT COUNT(*) FROM installations")).fetchone()[0]
        print(f"   Total records: {count}")
        
        if count > 0:
            rows = conn.execute(text("SELECT id, station_id, name, latitude, longitude, status FROM installations LIMIT 10")).fetchall()
            for row in rows:
                print(f"   #{row[0]}: station={row[1]}, name={row[2]}, lat={row[3]}, lon={row[4]}, status={row[5]}")
        
        # ── 5. SYSTEM HEALTH ──
        print(f"\n{'─'*80}")
        print(f"💚 TABLE: system_health")
        print(f"{'─'*80}")
        
        count = conn.execute(text("SELECT COUNT(*) FROM system_health")).fetchone()[0]
        print(f"   Total records: {count}")
        
        if count > 0:
            rows = conn.execute(text("SELECT id, station_id, timestamp, sensor_status, battery_level, connectivity FROM system_health ORDER BY timestamp DESC LIMIT 5")).fetchall()
            for row in rows:
                print(f"   #{row[0]}: station={row[1]}, time={row[2]}, status={row[3]}, battery={row[4]}, conn={row[5]}")
        
        # ── 6. TRENDS ──
        print(f"\n{'─'*80}")
        print(f"📈 TABLE: trends")
        print(f"{'─'*80}")
        
        count = conn.execute(text("SELECT COUNT(*) FROM trends")).fetchone()[0]
        print(f"   Total records: {count}")
        
        if count > 0:
            rows = conn.execute(text("SELECT id, station_id, metric, period, trend_direction, trend_rate, confidence FROM trends LIMIT 10")).fetchall()
            for row in rows:
                print(f"   #{row[0]}: station={row[1]}, {row[2]} ({row[3]}), direction={row[4]}, rate={row[5]}, confidence={row[6]}")
        
        # ── 7. USER PREFERENCES ──
        print(f"\n{'─'*80}")
        print(f"⚙️  TABLE: user_preferences")
        print(f"{'─'*80}")
        
        count = conn.execute(text("SELECT COUNT(*) FROM user_preferences")).fetchone()[0]
        print(f"   Total records: {count}")
        
        if count > 0:
            rows = conn.execute(text("SELECT id, user_id, preferred_unit, verbosity, alert_channel FROM user_preferences LIMIT 10")).fetchall()
            for row in rows:
                print(f"   #{row[0]}: user={row[1]}, unit={row[2]}, verbosity={row[3]}, channel={row[4]}")
    
    print(f"\n{'='*80}")
    print(f"✅ Query complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    query_all()
