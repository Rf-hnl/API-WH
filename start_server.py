#!/usr/bin/env python3
"""
Script para iniciar el servidor Flask del Bot WhatsApp Manager
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_port(port=5000):
    """Check if port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0

def kill_existing_processes():
    """Kill any existing Flask processes"""
    try:
        subprocess.run(['pkill', '-f', 'python.*app.py'], capture_output=True)
        subprocess.run(['lsof', '-ti:5000'], capture_output=True, check=False)
        time.sleep(2)
    except:
        pass

def main():
    print("🚀 Bot WhatsApp Manager - Starting Server")
    print("=" * 50)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Check if app.py exists
    if not Path('app.py').exists():
        print("❌ Error: app.py not found in current directory")
        sys.exit(1)
    
    # Kill existing processes
    print("🔄 Cleaning up existing processes...")
    kill_existing_processes()
    
    # Check if port is available
    if not check_port():
        print("❌ Error: Port 5000 is still in use")
        sys.exit(1)
    
    print("✅ Port 5000 is available")
    
    # Set environment variables
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    print("🌐 Starting Flask server...")
    print("📍 URLs disponibles:")
    print("   • Dashboard: http://127.0.0.1:5000")
    print("   • Conversaciones: http://127.0.0.1:5000/conversations")
    print("   • Enviar Mensaje: http://127.0.0.1:5000/send_message")
    print("   • Inquilinos: http://127.0.0.1:5000/tenants")
    print("   • API Webhook: http://127.0.0.1:5000/webhook/twilio")
    print("")
    print("🔧 Para detener el servidor: Ctrl+C")
    print("=" * 50)
    
    try:
        # Start Flask app
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por el usuario")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al iniciar el servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()