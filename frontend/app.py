import os
import subprocess

from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/progress.json')
def progress_json():
    """Serve il progress.json scritto in tempo reale da backend/src/progress_utils.py."""
    static_dir = os.path.join(app.root_path, 'static')
    return send_from_directory(static_dir, 'progress.json')


@app.route('/run', methods=['POST'])
def run_download():
    # Accetta sia JSON che form-data classico
    data = request.get_json(silent=True) or request.form
    url = (data.get('url') or '').strip()
    mode = (data.get('mode') or '').strip()  # "volumes" o "chapters"
    start = (data.get('start') or '').strip()
    end = (data.get('end') or '').strip()

    # --- Validazione ---
    if not url:
        return jsonify({'success': False, 'error': 'URL mancante'}), 400

    if mode not in ('volumes', 'chapters'):
        return jsonify({'success': False, 'error': 'Tipo non valido (deve essere "volumes" o "chapters")'}), 400

    # start ed end sono opzionali: li validiamo solo se presenti
    if start:
        try:
            start = int(start)
        except ValueError:
            return jsonify({'success': False, 'error': 'Start deve essere un numero intero'}), 400
        if start < 0:
            return jsonify({'success': False, 'error': 'Start non può essere negativo'}), 400
    else:
        start = None

    if end:
        try:
            end = int(end)
        except ValueError:
            return jsonify({'success': False, 'error': 'End deve essere un numero intero'}), 400
        if end < 0:
            return jsonify({'success': False, 'error': 'End non può essere negativo'}), 400
    else:
        end = None

    if start is not None and end is not None and end < start:
        return jsonify({'success': False, 'error': 'Intervallo start/end non valido'}), 400

    # --- Costruzione comando ---
    comando = ['python3', 'backend/manga_downloader.py', url, '--format', 'cbz']
    if mode == 'volumes':
        comando.append('--volume')
    # se mode è 'chapters' non aggiungiamo nessun flag
    if start is not None:
        comando += ['--start', str(start)]
    if end is not None:
        comando += ['--end', str(end)]

    # --- Esecuzione ---
    try:
        risultato = subprocess.run(
            comando,
            input='all\n',      # risponde automaticamente al prompt interattivo
            capture_output=True,
            text=True,
            timeout=3600  # timeout di sicurezza, adatta se serve
        )
        return jsonify({
            'success': risultato.returncode == 0,
            'stdout': risultato.stdout,
            'stderr': risultato.stderr,
            'returncode': risultato.returncode,
            'comando_eseguito': ' '.join(comando)
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Il comando ha superato il timeout'}), 500
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Script server.py non trovato nel percorso indicato'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6060)
