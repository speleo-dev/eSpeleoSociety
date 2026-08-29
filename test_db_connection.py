#!/usr/bin/env python3
"""Test pripojenia k PostgreSQL databaze na Websupport."""

import sys
sys.path.insert(0, '.')

def test_db_connection():
    """Otestuje pripojenie k databaze a vypise zakladne informacie."""
    print('=' * 60)
    print('DATABAZOVA KONFIGURACIA')
    print('=' * 60)
    
    try:
        # Načítanie secrets cez SecretManager s PINom
        from config import SecretManager
        sm = SecretManager()
        
        # Dešifrovanie s lokálnym PINom
        PIN = "00000000"
        if not sm.decrypt_file(PIN):
            print(f"CHYBA: Nepodarilo sa dešifrovat secrets.properties s PINom {PIN}")
            return False
        
        secrets = sm.secrets
        
        db_host = secrets.get('db_host', 'N/A')
        db_port = secrets.get('db_port', '5432')
        db_name = secrets.get('db_name', 'N/A')
        db_user = secrets.get('db_user', 'N/A')
        db_password_set = 'db_password' in secrets and secrets['db_password']
        
        print(f'Host:     {db_host}')
        print(f'Port:     {db_port}')
        print(f'Database: {db_name}')
        print(f'User:     {db_user}')
        print(f'Password: {"[NASTAVENE]" if db_password_set else "[CHYBA]"}')
        print('=' * 60)
        
        # Test pripojenia
        print()
        print('TEST PRIPOJENIA...')
        import psycopg2
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=secrets['db_password'],
            connect_timeout=10
        )
        print('✓ Pripojenie USPESNE!')
        
        # Test query
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        print(f'✓ PostgreSQL version: {version[:50]}...')
        
        # Zoznam tabuliek
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f'✓ Pocet tabuliek: {len(tables)}')
        print()
        print('TABULKY V DATABAZE:')
        for i, (table,) in enumerate(tables, 1):
            print(f'  {i:2}. {table}')
        
        # Počet členov
        cursor.execute('SELECT COUNT(*) FROM members;')
        member_count = cursor.fetchone()[0]
        print()
        print(f'POCET CLENOV: {member_count}')
        
        # Počet klubov
        cursor.execute('SELECT COUNT(*) FROM clubs;')
        club_count = cursor.fetchone()[0]
        print(f'POCET KLUBOV: {club_count}')
        
        cursor.close()
        conn.close()
        print()
        print('=' * 60)
        print('STAV: VSETKO FUNKCNE!')
        print('=' * 60)
        return True
        
    except Exception as e:
        print()
        print('=' * 60)
        print(f'CHYBA: {e}')
        print('=' * 60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_db_connection()
    sys.exit(0 if success else 1)
