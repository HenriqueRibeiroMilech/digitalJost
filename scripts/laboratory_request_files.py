import sys
import os
import shutil
import pandas as pd
from sqlalchemy import create_engine, text
import urllib

DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if DIR not in sys.path:
    sys.path.insert(0, DIR)

from app.utils.constants import CNNX_JDT

UPLOAD_ROOT = r'app\static\uploads\lab'

# Usa a string de conexão do constants.py
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_JDT)}")

def migrate_files():
    not_found = []
    errors = []
    with engine.connect() as conn:
        query = """
            SELECT requestId, drawFiles, reportFiles
            FROM JDT_REQUEST_LAB
        """
        df = pd.read_sql(text(query), conn)

        for _, row in df.iterrows():
            req_id = str(row['requestId'])
            base_dir = os.path.join(DIR, UPLOAD_ROOT, req_id)
            draw_dir = os.path.join(base_dir, 'draw')
            report_dir = os.path.join(base_dir, 'reports')

            # Verifica se a pasta raiz existe
            if not os.path.exists(base_dir):
                not_found.append({
                    'requestId': req_id,
                    'tipo': 'pasta_raiz',
                    'arquivo': '',
                    'mensagem': 'Pasta da solicitação não encontrada'
                })
                print(f'Pasta raiz não encontrada: {base_dir}')
                continue

            os.makedirs(draw_dir, exist_ok=True)
            os.makedirs(report_dir, exist_ok=True)

            found_any = False

            # Move arquivos de desenho
            if pd.notna(row['drawFiles']) and row['drawFiles'] not in ('', 'None'):
                for fname in row['drawFiles'].split('||'):
                    fname = fname.strip()
                    if fname:
                        src = os.path.join(base_dir, fname)
                        dst = os.path.join(draw_dir, fname)
                        try:
                            if os.path.exists(src):
                                shutil.move(src, dst)
                                print(f'Movido: {src} -> {dst}')
                                found_any = True
                            else:
                                not_found.append({
                                    'requestId': req_id,
                                    'tipo': 'draw',
                                    'arquivo': fname,
                                    'mensagem': 'Arquivo de desenho não encontrado'
                                })
                                print(f'Arquivo de desenho não encontrado: {src}')
                        except Exception as e:
                            errors.append({'requestId': req_id, 'arquivo': fname, 'tipo': 'draw', 'erro': str(e)})

            # Move arquivos de relatório
            if pd.notna(row['reportFiles']) and row['reportFiles'] not in ('', 'None'):
                for fname in row['reportFiles'].split('||'):
                    fname = fname.strip()
                    if fname:
                        src = os.path.join(base_dir, fname)
                        dst = os.path.join(report_dir, fname)
                        try:
                            if os.path.exists(src):
                                shutil.move(src, dst)
                                print(f'Movido: {src} -> {dst}')
                                found_any = True
                            else:
                                not_found.append({
                                    'requestId': req_id,
                                    'tipo': 'report',
                                    'arquivo': fname,
                                    'mensagem': 'Arquivo de relatório não encontrado'
                                })
                                print(f'Arquivo de relatório não encontrado: {src}')
                        except Exception as e:
                            errors.append({'requestId': req_id, 'arquivo': fname, 'tipo': 'report', 'erro': str(e)})

            # Se não encontrou nenhum arquivo para essa SSL, adiciona à lista (mas só se a pasta existir)
            if os.path.exists(base_dir) and not found_any:
                not_found.append({
                    'requestId': req_id,
                    'tipo': 'nenhum_arquivo',
                    'arquivo': '',
                    'mensagem': 'Nenhum arquivo encontrado para a solicitação'
                })

    print('\nSolicitações sem arquivos encontrados ou com problemas:')
    for nf in not_found:
        print(f"{nf['requestId']} - {nf['tipo']} - {nf['arquivo']} - {nf['mensagem']}")

    # Salva os not_found e erros em um Excel
    if not_found or errors:
        log_path = os.path.join(DIR, 'scripts', 'logs', 'erros_migracao_lab_files.xlsx')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with pd.ExcelWriter(log_path) as writer:            
            if not_found:
                pd.DataFrame(not_found).to_excel(writer, sheet_name='not_found', index=False)
            if errors:
                pd.DataFrame(errors).to_excel(writer, sheet_name='erros', index=False)
        print('\nArquivo erros_migracao_lab_files.xlsx gerado com os problemas encontrados.')

if __name__ == '__main__':
    migrate_files()
    print('Migração concluída.')