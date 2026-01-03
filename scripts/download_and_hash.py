import json
import hashlib
from datetime import datetime
from pathlib import Path

# Directorios
data_dir = Path("data")
hash_dir = Path("hashes")

data_dir.mkdir(exist_ok=True)
hash_dir.mkdir(exist_ok=True)

def get_previous_hash():
    # Busca el archivo de hash más reciente en hashes/
    hash_files = sorted(hash_dir.glob("*.sha256"), key=lambda p: p.stat().st_mtime, reverse=True)
    if hash_files:
        with open(hash_files[0], "r") as f:
            return f.read().strip()
    return None  # Si no hay previo, retorna None (primer run)

# Simulación (luego será el CNE – ajusta para requests.get(url))
sample_data = {
    "timestamp": datetime.utcnow().isoformat(),
    "example": "placeholder"
}

timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
json_path = data_dir / f"snapshot_{timestamp}.json"
hash_path = hash_dir / f"snapshot_{timestamp}.sha256"

# Guardar el snapshot JSON
with open(json_path, "w") as f:
    json.dump(sample_data, f, indent=2)

# Contenido para hash (sorted para consistencia)
content = json.dumps(sample_data, sort_keys=True).encode()

# Cargar hash previo para chaining
previous_hash = get_previous_hash()
if previous_hash:
    # Concatena hash previo al content para cadena inmutable
    content += previous_hash.encode()

# Calcular hash SHA-256
hash_value = hashlib.sha256(content).hexdigest()

# Guardar hash
with open(hash_path, "w") as f:
    f.write(hash_value)

print("Snapshot y hash chained creados:", timestamp)
print("Hash previo usado:", previous_hash or "Ninguno (primer run)")
print("Nuevo hash:", hash_value)
