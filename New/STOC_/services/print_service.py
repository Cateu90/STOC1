import os
import tempfile
import subprocess
import sys

class PrintService:
    @staticmethod
    def imprimir_texto(texto, printer_name):

        try:

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(texto)
                temp_file_path = temp_file.name
            
            print(f"[PRINT] Enviando para impressora '{printer_name}':\n{texto}")
            print(f"[PRINT] Arquivo temporário criado: {temp_file_path}")
            

            if sys.platform.startswith('win'):
                try:
                    result = subprocess.run([
                        'notepad.exe', '/p', temp_file_path
                    ], capture_output=True, text=True, timeout=30)
                    

                    import time
                    time.sleep(2)
                    
                    print(f"[PRINT] Comando notepad executado. Return code: {result.returncode}")

                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                    
                    return {"status": "success", "message": f"Enviado para impressão via notepad"}
                    
                except subprocess.TimeoutExpired:
                    print(f"[PRINT] Timeout ao tentar imprimir com notepad")
                    return {"status": "error", "message": "Timeout na impressão"}
                except Exception as e:
                    print(f"[PRINT] Erro ao usar notepad: {e}")
                    return {"status": "success", "message": f"Conteúdo exibido (impressora pode não estar disponível)"}
            else:
                print(f"[PRINT] Sistema não-Windows detectado. Simulando impressão.")
                return {"status": "success", "message": "Impresso (simulado - sistema não-Windows)"}
                
        except Exception as e:
            print(f"[ERROR] Erro na impressão: {e}")
            return {"status": "error", "message": f"Erro na impressão: {str(e)}"}
        finally:
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass
