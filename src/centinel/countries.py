"""
Presets de países de América Latina para Centinel.
Latin America country presets for Centinel.

Fuente de verdad para datos geográficos electorales.
Single source of truth for electoral geographic data.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


def _slugify(name: str) -> str:
    """Convert 'El Paraíso' → 'el_paraiso' for use as DB/slug keys."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


@dataclass
class CountryPreset:
    code: str
    name: str
    flag: str
    authority: str
    divisions_label: str
    divisions: List[str]
    division_iso_codes: List[str] = field(default_factory=list)
    # CNE numeric codes for each division, in the same order as divisions[].
    # "00" is reserved for the national (TODOS) level.
    # Example HN: ["01","02",...,"18"] matches the CNE URL /departamento/01 etc.
    division_cne_codes: List[str] = field(default_factory=list)
    url_pattern: Optional[str] = None
    national_url: Optional[str] = None
    national_cne_code: str = "00"          # CNE code for the national scope
    national_filename_pattern: Optional[str] = None
    notes: Optional[str] = None

    @property
    def divisions_count(self) -> int:
        return len(self.divisions)

    def build_dept_maps(self) -> Tuple[Dict[str, str], Dict[str, str], List[str]]:
        """Return (slug_to_iso, iso_to_name, slugs) for use in the API."""
        slugs = [_slugify(d) for d in self.divisions]
        slug_to_iso: Dict[str, str] = {}
        iso_to_name: Dict[str, str] = {}

        for i, (div_name, slug) in enumerate(zip(self.divisions, slugs)):
            if self.division_iso_codes and i < len(self.division_iso_codes):
                iso = self.division_iso_codes[i]
            else:
                iso = f"{self.code}-{slug[:2].upper()}"
            slug_to_iso[slug] = iso
            iso_to_name[iso] = div_name

        return slug_to_iso, iso_to_name, slugs

    def build_cne_map(self) -> Dict[str, str]:
        """Return {cne_code: division_name} including the national entry.

        Example: {"00": "TODOS", "01": "Atlántida", ..., "18": "Yoro"}
        """
        result: Dict[str, str] = {self.national_cne_code: "TODOS"}
        for i, div_name in enumerate(self.divisions):
            if self.division_cne_codes and i < len(self.division_cne_codes):
                code = self.division_cne_codes[i]
            else:
                code = f"{i + 1:02d}"
            result[code] = div_name
        return result

    def slug_to_cne(self, slug: str) -> Optional[str]:
        """Return the CNE numeric code for a department slug, e.g. 'atlantida' → '01'."""
        slugs = [_slugify(d) for d in self.divisions]
        try:
            idx = slugs.index(slug)
        except ValueError:
            return None
        if self.division_cne_codes and idx < len(self.division_cne_codes):
            return self.division_cne_codes[idx]
        return f"{idx + 1:02d}"


LATAM_COUNTRIES: Dict[str, CountryPreset] = {
    "HN": CountryPreset(
        code="HN",
        name="Honduras",
        flag="🇭🇳",
        authority="Consejo Nacional Electoral (CNE)",
        divisions_label="Departamentos",
        divisions=[
            "Atlántida", "Choluteca", "Colón", "Comayagua",
            "Copán", "Cortés", "El Paraíso", "Francisco Morazán",
            "Gracias a Dios", "Intibucá", "Islas de la Bahía",
            "La Paz", "Lempira", "Ocotepeque", "Olancho",
            "Santa Bárbara", "Valle", "Yoro",
        ],
        # ISO 3166-2:HN codes in the same order as divisions above
        division_iso_codes=[
            "HN-AT", "HN-CH", "HN-CL", "HN-CM",
            "HN-CP", "HN-CR", "HN-EP", "HN-FM",
            "HN-GD", "HN-IN", "HN-IB",
            "HN-LP", "HN-LE", "HN-OC", "HN-OL",
            "HN-SB", "HN-VA", "HN-YO",
        ],
        # CNE numeric codes: 00=TODOS, 01=Atlántida … 18=Yoro
        # These are the numbers used in CNE API URLs and filenames.
        division_cne_codes=[
            "01", "02", "03", "04",
            "05", "06", "07", "08",
            "09", "10", "11",
            "12", "13", "14", "15",
            "16", "17", "18",
        ],
        national_cne_code="00",
        url_pattern="https://resultadosgenerales2025.cne.hn/api/presidencial/departamento/{cne_code}",
        national_url="https://resultadosgenerales2025.cne.hn/api/presidencial/nacional",
        national_filename_pattern=r"(\d{4}-\d{2}-\d{2} \d{2}_\d{2}_\d{2})",
    ),
    "GT": CountryPreset(
        code="GT",
        name="Guatemala",
        flag="🇬🇹",
        authority="Tribunal Supremo Electoral (TSE)",
        divisions_label="Departamentos",
        divisions=[
            "Alta Verapaz", "Baja Verapaz", "Chimaltenango", "Chiquimula",
            "El Progreso", "Escuintla", "Guatemala", "Huehuetenango",
            "Izabal", "Jalapa", "Jutiapa", "Petén",
            "Quetzaltenango", "Quiché", "Retalhuleu", "Sacatepéquez",
            "San Marcos", "Santa Rosa", "Sololá", "Suchitepéquez",
            "Totonicapán", "Zacapa",
        ],
        url_pattern="https://resultados.tse.org.gt/api/actas/{division}",
    ),
    "SV": CountryPreset(
        code="SV",
        name="El Salvador",
        flag="🇸🇻",
        authority="Tribunal Supremo Electoral (TSE)",
        divisions_label="Departamentos",
        divisions=[
            "Ahuachapán", "Cabañas", "Chalatenango", "Cuscatlán",
            "La Libertad", "La Paz", "La Unión", "Morazán",
            "San Miguel", "San Salvador", "San Vicente",
            "Santa Ana", "Sonsonate", "Usulután",
        ],
        url_pattern="https://resultados.tse.gob.sv/api/actas/{division}",
    ),
    "NI": CountryPreset(
        code="NI",
        name="Nicaragua",
        flag="🇳🇮",
        authority="Consejo Supremo Electoral (CSE)",
        divisions_label="Departamentos",
        divisions=[
            "Boaco", "Carazo", "Chinandega", "Chontales",
            "Estelí", "Granada", "Jinotega", "León",
            "Madriz", "Managua", "Masaya", "Matagalpa",
            "Nueva Segovia", "Río San Juan", "Rivas",
            "RACCN", "RACCS",
        ],
        url_pattern="https://resultados.cse.gob.ni/api/actas/{division}",
    ),
    "CR": CountryPreset(
        code="CR",
        name="Costa Rica",
        flag="🇨🇷",
        authority="Tribunal Supremo de Elecciones (TSE)",
        divisions_label="Provincias",
        divisions=[
            "Alajuela", "Cartago", "Guanacaste", "Heredia",
            "Limón", "Puntarenas", "San José",
        ],
        url_pattern="https://resultados.tse.go.cr/api/actas/{division}",
    ),
    "PA": CountryPreset(
        code="PA",
        name="Panamá",
        flag="🇵🇦",
        authority="Tribunal Electoral (TE)",
        divisions_label="Provincias",
        divisions=[
            "Bocas del Toro", "Chiriquí", "Coclé", "Colón",
            "Darién", "Herrera", "Los Santos", "Panamá",
            "Panamá Oeste", "Veraguas",
            "Comarca Guna Yala", "Comarca Emberá", "Comarca Ngäbe-Buglé",
        ],
        url_pattern="https://resultados.tribunal-electoral.gob.pa/api/actas/{division}",
    ),
    "MX": CountryPreset(
        code="MX",
        name="México",
        flag="🇲🇽",
        authority="Instituto Nacional Electoral (INE)",
        divisions_label="Estados",
        divisions=[
            "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
            "Chiapas", "Chihuahua", "Ciudad de México", "Coahuila",
            "Colima", "Durango", "Guanajuato", "Guerrero",
            "Hidalgo", "Jalisco", "México", "Michoacán",
            "Morelos", "Nayarit", "Nuevo León", "Oaxaca",
            "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
            "Sinaloa", "Sonora", "Tabasco", "Tamaulipas",
            "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
        ],
        url_pattern="https://prep2024.ine.mx/api/actas/{division}",
    ),
    "CO": CountryPreset(
        code="CO",
        name="Colombia",
        flag="🇨🇴",
        authority="Registraduría Nacional del Estado Civil",
        divisions_label="Departamentos",
        divisions=[
            "Amazonas", "Antioquia", "Arauca", "Atlántico",
            "Bolívar", "Boyacá", "Caldas", "Caquetá",
            "Casanare", "Cauca", "Cesar", "Chocó",
            "Córdoba", "Cundinamarca", "Guainía", "Guaviare",
            "Huila", "La Guajira", "Magdalena", "Meta",
            "Nariño", "Norte de Santander", "Putumayo", "Quindío",
            "Risaralda", "San Andrés y Providencia", "Santander", "Sucre",
            "Tolima", "Valle del Cauca", "Vaupés", "Vichada",
            "Bogotá D.C.",
        ],
        url_pattern="https://resultados.registraduria.gov.co/api/actas/{division}",
    ),
    "VE": CountryPreset(
        code="VE",
        name="Venezuela",
        flag="🇻🇪",
        authority="Consejo Nacional Electoral (CNE)",
        divisions_label="Estados",
        divisions=[
            "Amazonas", "Anzoátegui", "Apure", "Aragua",
            "Barinas", "Bolívar", "Carabobo", "Cojedes",
            "Delta Amacuro", "Falcón", "Guárico", "La Guaira",
            "Lara", "Mérida", "Miranda", "Monagas",
            "Nueva Esparta", "Portuguesa", "Sucre", "Táchira",
            "Trujillo", "Yaracuy", "Zulia",
            "Distrito Capital",
        ],
        url_pattern="https://resultados.cne.gob.ve/api/actas/{division}",
    ),
    "PE": CountryPreset(
        code="PE",
        name="Perú",
        flag="🇵🇪",
        authority="Jurado Nacional de Elecciones (JNE) / ONPE",
        divisions_label="Regiones",
        divisions=[
            "Amazonas", "Áncash", "Apurímac", "Arequipa",
            "Ayacucho", "Cajamarca", "Callao", "Cusco",
            "Huancavelica", "Huánuco", "Ica", "Junín",
            "La Libertad", "Lambayeque", "Lima", "Loreto",
            "Madre de Dios", "Moquegua", "Pasco", "Piura",
            "Puno", "San Martín", "Tacna", "Tumbes",
            "Ucayali",
        ],
        url_pattern="https://resultados.onpe.gob.pe/api/actas/{division}",
    ),
    "EC": CountryPreset(
        code="EC",
        name="Ecuador",
        flag="🇪🇨",
        authority="Consejo Nacional Electoral (CNE)",
        divisions_label="Provincias",
        divisions=[
            "Azuay", "Bolívar", "Cañar", "Carchi",
            "Chimborazo", "Cotopaxi", "El Oro", "Esmeraldas",
            "Galápagos", "Guayas", "Imbabura", "Loja",
            "Los Ríos", "Manabí", "Morona Santiago", "Napo",
            "Orellana", "Pastaza", "Pichincha", "Santa Elena",
            "Santo Domingo de los Tsáchilas", "Sucumbíos", "Tungurahua", "Zamora Chinchipe",
        ],
        url_pattern="https://resultados.cne.gob.ec/api/actas/{division}",
    ),
    "BO": CountryPreset(
        code="BO",
        name="Bolivia",
        flag="🇧🇴",
        authority="Tribunal Supremo Electoral (TSE)",
        divisions_label="Departamentos",
        divisions=[
            "Beni", "Chuquisaca", "Cochabamba", "La Paz",
            "Oruro", "Pando", "Potosí", "Santa Cruz",
            "Tarija",
        ],
        url_pattern="https://resultados.oep.org.bo/api/actas/{division}",
    ),
    "CL": CountryPreset(
        code="CL",
        name="Chile",
        flag="🇨🇱",
        authority="Servicio Electoral (SERVEL)",
        divisions_label="Regiones",
        divisions=[
            "Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama",
            "Coquimbo", "Valparaíso", "Metropolitana de Santiago", "O'Higgins",
            "Maule", "Ñuble", "Biobío", "La Araucanía",
            "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
        ],
        url_pattern="https://resultados.servel.cl/api/actas/{division}",
    ),
    "AR": CountryPreset(
        code="AR",
        name="Argentina",
        flag="🇦🇷",
        authority="Cámara Nacional Electoral (CNE)",
        divisions_label="Provincias",
        divisions=[
            "Buenos Aires", "Buenos Aires (Ciudad)", "Catamarca", "Chaco",
            "Chubut", "Córdoba", "Corrientes", "Entre Ríos",
            "Formosa", "Jujuy", "La Pampa", "La Rioja",
            "Mendoza", "Misiones", "Neuquén", "Río Negro",
            "Salta", "San Juan", "San Luis", "Santa Cruz",
            "Santa Fe", "Santiago del Estero", "Tierra del Fuego", "Tucumán",
        ],
        url_pattern="https://resultados.padron.gob.ar/api/actas/{division}",
    ),
    "UY": CountryPreset(
        code="UY",
        name="Uruguay",
        flag="🇺🇾",
        authority="Corte Electoral",
        divisions_label="Departamentos",
        divisions=[
            "Artigas", "Canelones", "Cerro Largo", "Colonia",
            "Durazno", "Flores", "Florida", "Lavalleja",
            "Maldonado", "Montevideo", "Paysandú", "Río Negro",
            "Rivera", "Rocha", "Salto", "San José",
            "Soriano", "Tacuarembó", "Treinta y Tres",
        ],
        url_pattern="https://resultados.corteelectoral.gub.uy/api/actas/{division}",
    ),
    "PY": CountryPreset(
        code="PY",
        name="Paraguay",
        flag="🇵🇾",
        authority="Tribunal Superior de Justicia Electoral (TSJE)",
        divisions_label="Departamentos",
        divisions=[
            "Alto Paraguay", "Alto Paraná", "Amambay", "Asunción",
            "Boquerón", "Caaguazú", "Caazapá", "Canindeyú",
            "Central", "Concepción", "Cordillera", "Guairá",
            "Itapúa", "Misiones", "Ñeembucú", "Paraguarí",
            "Presidente Hayes", "San Pedro",
        ],
        url_pattern="https://resultados.tsje.gov.py/api/actas/{division}",
    ),
    "BR": CountryPreset(
        code="BR",
        name="Brasil",
        flag="🇧🇷",
        authority="Tribunal Superior Electoral (TSE)",
        divisions_label="Estados",
        divisions=[
            "Acre", "Alagoas", "Amapá", "Amazonas",
            "Bahia", "Ceará", "Distrito Federal", "Espírito Santo",
            "Goiás", "Maranhão", "Mato Grosso", "Mato Grosso do Sul",
            "Minas Gerais", "Pará", "Paraíba", "Paraná",
            "Pernambuco", "Piauí", "Rio de Janeiro", "Rio Grande do Norte",
            "Rio Grande do Sul", "Rondônia", "Roraima", "Santa Catarina",
            "São Paulo", "Sergipe", "Tocantins",
        ],
        url_pattern="https://resultados.tse.jus.br/api/actas/{division}",
        notes="Sistema de urna electrónica. Auditoría de logs de UE.",
    ),
    "DO": CountryPreset(
        code="DO",
        name="República Dominicana",
        flag="🇩🇴",
        authority="Junta Central Electoral (JCE)",
        divisions_label="Provincias",
        divisions=[
            "Azua", "Bahoruco", "Barahona", "Dajabón",
            "Distrito Nacional", "Duarte", "El Seibo", "Elías Piña",
            "Espaillat", "Hato Mayor", "Hermanas Mirabal", "Independencia",
            "La Altagracia", "La Romana", "La Vega", "María Trinidad Sánchez",
            "Monseñor Nouel", "Monte Cristi", "Monte Plata", "Pedernales",
            "Peravia", "Puerto Plata", "Samaná", "San Cristóbal",
            "San José de Ocoa", "San Juan", "San Pedro de Macorís", "Sánchez Ramírez",
            "Santiago", "Santiago Rodríguez", "Santo Domingo", "Valverde",
        ],
        url_pattern="https://resultados.jce.gob.do/api/actas/{division}",
    ),
    "CU": CountryPreset(
        code="CU",
        name="Cuba",
        flag="🇨🇺",
        authority="Consejo Electoral Nacional",
        divisions_label="Provincias",
        divisions=[
            "Artemisa", "Camagüey", "Ciego de Ávila", "Cienfuegos",
            "Granma", "Guantánamo", "Holguín", "La Habana",
            "Las Tunas", "Matanzas", "Mayabeque", "Pinar del Río",
            "Sancti Spíritus", "Santiago de Cuba", "Villa Clara",
            "Isla de la Juventud",
        ],
        url_pattern=None,
        notes="Acceso a datos electorales altamente restringido.",
    ),
    "HT": CountryPreset(
        code="HT",
        name="Haití",
        flag="🇭🇹",
        authority="Conseil Electoral Provisoire (CEP)",
        divisions_label="Departamentos",
        divisions=[
            "Artibonite", "Centre", "Grand'Anse", "Nippes",
            "Nord", "Nord-Est", "Nord-Ouest", "Ouest",
            "Sud", "Sud-Est",
        ],
        url_pattern=None,
        notes="Proceso electoral intermitente. Verificar disponibilidad de datos.",
    ),
}


def get_country(code: str) -> CountryPreset:
    """Retorna preset por código ISO. Lanza KeyError si no existe."""
    code = code.upper().strip()
    if code not in LATAM_COUNTRIES:
        available = ", ".join(sorted(LATAM_COUNTRIES.keys()))
        raise KeyError(f"País '{code}' no encontrado. Disponibles: {available}")
    return LATAM_COUNTRIES[code]


def list_countries() -> List[CountryPreset]:
    """Retorna todos los países ordenados por nombre."""
    return sorted(LATAM_COUNTRIES.values(), key=lambda c: c.name)
