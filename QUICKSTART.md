# QUICKSTART

## Inicio rápido (ES)

1. **Clona el repositorio**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd sentinel
   ```

2. **Crea el archivo `.env`**
   ```bash
   cp .env.example .env
   ```
   > Si no existe un `.env.example`, crea `.env` manualmente con tus variables locales.

3. **Configura `config.yaml`**
   ```bash
   cp config.example.yaml config.yaml
   ```
   Edita `config.yaml` con la URL base, headers y fuentes de tu entorno.

4. **Instala dependencias**
   ```bash
   pip install -r requirements.txt
   ```

5. **Ejecuta el pipeline de datos**
   ```bash
   python scripts/download_and_hash.py
   python scripts/analyze_rules.py
   ```
   - Salidas principales: `reports/` y `analysis_results.json`.

6. **Lanza el dashboard**
   ```bash
   streamlit run dashboard.py
   ```

---

## Quickstart (EN)

1. **Clone the repository**
   ```bash
   git clone <REPOSITORY_URL>
   cd sentinel
   ```

2. **Create the `.env` file**
   ```bash
   cp .env.example .env
   ```
   > If `.env.example` is not available, create `.env` manually with your local variables.

3. **Configure `config.yaml`**
   ```bash
   cp config.example.yaml config.yaml
   ```
   Edit `config.yaml` with the base URL, headers, and sources for your environment.

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the data pipeline**
   ```bash
   python scripts/download_and_hash.py
   python scripts/analyze_rules.py
   ```
   - Main outputs: `reports/` and `analysis_results.json`.

6. **Launch the dashboard**
   ```bash
   streamlit run dashboard.py
   ```
