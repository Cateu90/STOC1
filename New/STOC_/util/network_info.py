import socket
import os
import subprocess
import platform

def get_network_ip():
    """
    Detecta o IP da rede local de forma mais robusta
    """
    try:
        # Método 1: Socket connect (mais confiável)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Conecta com um IP externo para forçar o sistema a escolher o IP local
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        
        if ip and ip != '127.0.0.1':
            print(f"[INFO] IP detectado via socket: {ip}")
            return ip
            
    except Exception as e:
        print(f"[WARNING] Erro no método socket: {e}")
    
    try:
        # Método 2: Usando comando do sistema
        system = platform.system().lower()
        
        if system == "windows":
            # No Windows, usa ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, shell=True)
            lines = result.stdout.split('\n')
            
            for line in lines:
                if 'IPv4' in line and 'Endereço' in line:
                    # Extrai o IP da linha
                    ip = line.split(':')[-1].strip()
                    if (ip and ip != '127.0.0.1' and 
                        not ip.startswith('169.254') and  # APIPA
                        '.' in ip):
                        print(f"[INFO] IP detectado via ipconfig: {ip}")
                        return ip
        
        elif system in ["linux", "darwin"]:  # Linux ou macOS
            # Usa ifconfig ou ip
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                if result.returncode == 0:
                    ips = result.stdout.strip().split()
                    for ip in ips:
                        if (ip and ip != '127.0.0.1' and 
                            not ip.startswith('169.254') and
                            '.' in ip):
                            print(f"[INFO] IP detectado via hostname: {ip}")
                            return ip
            except:
                pass
                    
    except Exception as e:
        print(f"[WARNING] Erro no método sistema: {e}")
    
    try:
        # Método 3: Hostname (último recurso)
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != '127.0.0.1':
            print(f"[INFO] IP detectado via hostname: {ip}")
            return ip
    except Exception as e:
        print(f"[WARNING] Erro no método hostname: {e}")
    
    # Se nada funcionar, retorna localhost
    print("[WARNING] Não foi possível detectar o IP da rede, usando localhost")
    return '127.0.0.1'

def get_ip_and_port():
    """
    Retorna o IP da rede local e a porta do servidor
    """
    ip = get_network_ip()
    port = int(os.getenv('PORT', '8000'))  # Converter para inteiro
    return ip, port
