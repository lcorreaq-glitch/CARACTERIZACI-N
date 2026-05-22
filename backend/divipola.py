"""DIVIPOLA — minimal mapping of Colombian municipalities (Antioquia priority) with lat/lon.
Used to geolocate students for the territorial dashboard.
Codes here are the standard DANE municipal codes (5 digits) when available.
The legacy institutional Excel uses internal numeric IDs which we map by name fuzzy-matched
to the closest known municipality during ingestion (best-effort).
"""

# Antioquia main municipalities + Colombian capitals + bordering departments
MUNICIPIOS = [
    # Antioquia priority
    {"codigo": "05001", "nombre": "MEDELLIN", "departamento": "ANTIOQUIA", "lat": 6.2442, "lon": -75.5812},
    {"codigo": "05002", "nombre": "ABEJORRAL", "departamento": "ANTIOQUIA", "lat": 5.7894, "lon": -75.4283},
    {"codigo": "05004", "nombre": "ABRIAQUI", "departamento": "ANTIOQUIA", "lat": 6.6325, "lon": -76.0633},
    {"codigo": "05021", "nombre": "ALEJANDRIA", "departamento": "ANTIOQUIA", "lat": 6.3756, "lon": -75.1417},
    {"codigo": "05030", "nombre": "AMAGA", "departamento": "ANTIOQUIA", "lat": 6.0386, "lon": -75.7028},
    {"codigo": "05031", "nombre": "AMALFI", "departamento": "ANTIOQUIA", "lat": 6.9094, "lon": -75.0772},
    {"codigo": "05034", "nombre": "ANDES", "departamento": "ANTIOQUIA", "lat": 5.6553, "lon": -75.8783},
    {"codigo": "05036", "nombre": "ANGELOPOLIS", "departamento": "ANTIOQUIA", "lat": 6.1100, "lon": -75.7100},
    {"codigo": "05038", "nombre": "ANGOSTURA", "departamento": "ANTIOQUIA", "lat": 6.8853, "lon": -75.3389},
    {"codigo": "05040", "nombre": "ANORI", "departamento": "ANTIOQUIA", "lat": 7.0742, "lon": -75.1456},
    {"codigo": "05042", "nombre": "SANTAFE DE ANTIOQUIA", "departamento": "ANTIOQUIA", "lat": 6.5569, "lon": -75.8281},
    {"codigo": "05044", "nombre": "ANZA", "departamento": "ANTIOQUIA", "lat": 6.3083, "lon": -75.8531},
    {"codigo": "05045", "nombre": "APARTADO", "departamento": "ANTIOQUIA", "lat": 7.8839, "lon": -76.6253},
    {"codigo": "05051", "nombre": "ARBOLETES", "departamento": "ANTIOQUIA", "lat": 8.8500, "lon": -76.4283},
    {"codigo": "05055", "nombre": "ARGELIA", "departamento": "ANTIOQUIA", "lat": 5.7256, "lon": -75.1411},
    {"codigo": "05059", "nombre": "ARMENIA", "departamento": "ANTIOQUIA", "lat": 6.1561, "lon": -75.7847},
    {"codigo": "05079", "nombre": "BARBOSA", "departamento": "ANTIOQUIA", "lat": 6.4392, "lon": -75.3322},
    {"codigo": "05086", "nombre": "BELMIRA", "departamento": "ANTIOQUIA", "lat": 6.6053, "lon": -75.6661},
    {"codigo": "05088", "nombre": "BELLO", "departamento": "ANTIOQUIA", "lat": 6.3373, "lon": -75.5586},
    {"codigo": "05091", "nombre": "BETANIA", "departamento": "ANTIOQUIA", "lat": 5.7461, "lon": -75.9728},
    {"codigo": "05093", "nombre": "BETULIA", "departamento": "ANTIOQUIA", "lat": 6.1133, "lon": -75.9794},
    {"codigo": "05101", "nombre": "CIUDAD BOLIVAR", "departamento": "ANTIOQUIA", "lat": 5.8497, "lon": -76.0214},
    {"codigo": "05107", "nombre": "BRICEÑO", "departamento": "ANTIOQUIA", "lat": 7.1131, "lon": -75.5500},
    {"codigo": "05113", "nombre": "BURITICA", "departamento": "ANTIOQUIA", "lat": 6.7203, "lon": -75.9078},
    {"codigo": "05120", "nombre": "CACERES", "departamento": "ANTIOQUIA", "lat": 7.5781, "lon": -75.3503},
    {"codigo": "05125", "nombre": "CAICEDO", "departamento": "ANTIOQUIA", "lat": 6.4053, "lon": -75.9750},
    {"codigo": "05129", "nombre": "CALDAS", "departamento": "ANTIOQUIA", "lat": 6.0917, "lon": -75.6361},
    {"codigo": "05134", "nombre": "CAMPAMENTO", "departamento": "ANTIOQUIA", "lat": 6.9786, "lon": -75.2972},
    {"codigo": "05138", "nombre": "CAÑASGORDAS", "departamento": "ANTIOQUIA", "lat": 6.7522, "lon": -76.0269},
    {"codigo": "05142", "nombre": "CARACOLI", "departamento": "ANTIOQUIA", "lat": 6.4083, "lon": -74.7556},
    {"codigo": "05145", "nombre": "CARAMANTA", "departamento": "ANTIOQUIA", "lat": 5.5494, "lon": -75.6383},
    {"codigo": "05147", "nombre": "CAREPA", "departamento": "ANTIOQUIA", "lat": 7.7561, "lon": -76.6531},
    {"codigo": "05148", "nombre": "EL CARMEN DE VIBORAL", "departamento": "ANTIOQUIA", "lat": 6.0828, "lon": -75.3361},
    {"codigo": "05150", "nombre": "CAROLINA", "departamento": "ANTIOQUIA", "lat": 6.7253, "lon": -75.2839},
    {"codigo": "05154", "nombre": "CAUCASIA", "departamento": "ANTIOQUIA", "lat": 7.9869, "lon": -75.1981},
    {"codigo": "05172", "nombre": "CHIGORODO", "departamento": "ANTIOQUIA", "lat": 7.6669, "lon": -76.6814},
    {"codigo": "05190", "nombre": "CISNEROS", "departamento": "ANTIOQUIA", "lat": 6.5383, "lon": -75.0875},
    {"codigo": "05197", "nombre": "COCORNA", "departamento": "ANTIOQUIA", "lat": 6.0581, "lon": -75.1856},
    {"codigo": "05206", "nombre": "CONCEPCION", "departamento": "ANTIOQUIA", "lat": 6.3942, "lon": -75.2581},
    {"codigo": "05209", "nombre": "CONCORDIA", "departamento": "ANTIOQUIA", "lat": 6.0458, "lon": -75.9056},
    {"codigo": "05212", "nombre": "COPACABANA", "departamento": "ANTIOQUIA", "lat": 6.3478, "lon": -75.5078},
    {"codigo": "05234", "nombre": "DABEIBA", "departamento": "ANTIOQUIA", "lat": 6.9994, "lon": -76.2664},
    {"codigo": "05237", "nombre": "DONMATIAS", "departamento": "ANTIOQUIA", "lat": 6.4853, "lon": -75.3942},
    {"codigo": "05240", "nombre": "EBEJICO", "departamento": "ANTIOQUIA", "lat": 6.3261, "lon": -75.7644},
    {"codigo": "05250", "nombre": "EL BAGRE", "departamento": "ANTIOQUIA", "lat": 7.6033, "lon": -74.8081},
    {"codigo": "05264", "nombre": "ENTRERRIOS", "departamento": "ANTIOQUIA", "lat": 6.5631, "lon": -75.5169},
    {"codigo": "05266", "nombre": "ENVIGADO", "departamento": "ANTIOQUIA", "lat": 6.1717, "lon": -75.5917},
    {"codigo": "05282", "nombre": "FREDONIA", "departamento": "ANTIOQUIA", "lat": 5.9275, "lon": -75.6736},
    {"codigo": "05284", "nombre": "FRONTINO", "departamento": "ANTIOQUIA", "lat": 6.7747, "lon": -76.1311},
    {"codigo": "05306", "nombre": "GIRALDO", "departamento": "ANTIOQUIA", "lat": 6.6789, "lon": -75.9569},
    {"codigo": "05308", "nombre": "GIRARDOTA", "departamento": "ANTIOQUIA", "lat": 6.3789, "lon": -75.4453},
    {"codigo": "05310", "nombre": "GOMEZ PLATA", "departamento": "ANTIOQUIA", "lat": 6.6817, "lon": -75.2197},
    {"codigo": "05313", "nombre": "GRANADA", "departamento": "ANTIOQUIA", "lat": 6.1431, "lon": -75.1850},
    {"codigo": "05315", "nombre": "GUADALUPE", "departamento": "ANTIOQUIA", "lat": 6.8147, "lon": -75.2392},
    {"codigo": "05318", "nombre": "GUARNE", "departamento": "ANTIOQUIA", "lat": 6.2792, "lon": -75.4419},
    {"codigo": "05321", "nombre": "GUATAPE", "departamento": "ANTIOQUIA", "lat": 6.2331, "lon": -75.1597},
    {"codigo": "05347", "nombre": "HELICONIA", "departamento": "ANTIOQUIA", "lat": 6.2069, "lon": -75.7350},
    {"codigo": "05353", "nombre": "HISPANIA", "departamento": "ANTIOQUIA", "lat": 5.7997, "lon": -75.9050},
    {"codigo": "05360", "nombre": "ITAGUI", "departamento": "ANTIOQUIA", "lat": 6.1719, "lon": -75.6097},
    {"codigo": "05361", "nombre": "ITUANGO", "departamento": "ANTIOQUIA", "lat": 7.1719, "lon": -75.7639},
    {"codigo": "05364", "nombre": "JARDIN", "departamento": "ANTIOQUIA", "lat": 5.5994, "lon": -75.8197},
    {"codigo": "05368", "nombre": "JERICO", "departamento": "ANTIOQUIA", "lat": 5.7906, "lon": -75.7858},
    {"codigo": "05376", "nombre": "LA CEJA", "departamento": "ANTIOQUIA", "lat": 6.0319, "lon": -75.4292},
    {"codigo": "05380", "nombre": "LA ESTRELLA", "departamento": "ANTIOQUIA", "lat": 6.1597, "lon": -75.6447},
    {"codigo": "05390", "nombre": "LA PINTADA", "departamento": "ANTIOQUIA", "lat": 5.7464, "lon": -75.6064},
    {"codigo": "05400", "nombre": "LA UNION", "departamento": "ANTIOQUIA", "lat": 5.9742, "lon": -75.3597},
    {"codigo": "05411", "nombre": "LIBORINA", "departamento": "ANTIOQUIA", "lat": 6.6789, "lon": -75.8136},
    {"codigo": "05425", "nombre": "MACEO", "departamento": "ANTIOQUIA", "lat": 6.5556, "lon": -74.7869},
    {"codigo": "05440", "nombre": "MARINILLA", "departamento": "ANTIOQUIA", "lat": 6.1736, "lon": -75.3375},
    {"codigo": "05467", "nombre": "MONTEBELLO", "departamento": "ANTIOQUIA", "lat": 5.9447, "lon": -75.5247},
    {"codigo": "05475", "nombre": "MURINDO", "departamento": "ANTIOQUIA", "lat": 6.9806, "lon": -76.7672},
    {"codigo": "05480", "nombre": "MUTATA", "departamento": "ANTIOQUIA", "lat": 7.2436, "lon": -76.4361},
    {"codigo": "05483", "nombre": "NARIÑO", "departamento": "ANTIOQUIA", "lat": 5.6094, "lon": -75.1769},
    {"codigo": "05490", "nombre": "NECOCLI", "departamento": "ANTIOQUIA", "lat": 8.4239, "lon": -76.7853},
    {"codigo": "05495", "nombre": "NECHI", "departamento": "ANTIOQUIA", "lat": 8.0931, "lon": -74.7758},
    {"codigo": "05501", "nombre": "OLAYA", "departamento": "ANTIOQUIA", "lat": 6.6256, "lon": -75.8092},
    {"codigo": "05541", "nombre": "PEÑOL", "departamento": "ANTIOQUIA", "lat": 6.2206, "lon": -75.2447},
    {"codigo": "05543", "nombre": "PEQUE", "departamento": "ANTIOQUIA", "lat": 7.0214, "lon": -75.9100},
    {"codigo": "05576", "nombre": "PUEBLORRICO", "departamento": "ANTIOQUIA", "lat": 5.7920, "lon": -75.8419},
    {"codigo": "05579", "nombre": "PUERTO BERRIO", "departamento": "ANTIOQUIA", "lat": 6.4878, "lon": -74.4044},
    {"codigo": "05585", "nombre": "PUERTO NARE", "departamento": "ANTIOQUIA", "lat": 6.1928, "lon": -74.5839},
    {"codigo": "05591", "nombre": "PUERTO TRIUNFO", "departamento": "ANTIOQUIA", "lat": 5.8722, "lon": -74.6406},
    {"codigo": "05604", "nombre": "REMEDIOS", "departamento": "ANTIOQUIA", "lat": 7.0289, "lon": -74.7000},
    {"codigo": "05607", "nombre": "RETIRO", "departamento": "ANTIOQUIA", "lat": 6.0606, "lon": -75.5028},
    {"codigo": "05615", "nombre": "RIONEGRO", "departamento": "ANTIOQUIA", "lat": 6.1547, "lon": -75.3744},
    {"codigo": "05628", "nombre": "SABANALARGA", "departamento": "ANTIOQUIA", "lat": 6.8472, "lon": -75.8169},
    {"codigo": "05631", "nombre": "SABANETA", "departamento": "ANTIOQUIA", "lat": 6.1511, "lon": -75.6164},
    {"codigo": "05642", "nombre": "SALGAR", "departamento": "ANTIOQUIA", "lat": 5.9636, "lon": -75.9756},
    {"codigo": "05647", "nombre": "SAN ANDRES DE CUERQUIA", "departamento": "ANTIOQUIA", "lat": 6.9156, "lon": -75.6753},
    {"codigo": "05649", "nombre": "SAN CARLOS", "departamento": "ANTIOQUIA", "lat": 6.1881, "lon": -74.9933},
    {"codigo": "05652", "nombre": "SAN FRANCISCO", "departamento": "ANTIOQUIA", "lat": 5.9636, "lon": -75.1019},
    {"codigo": "05656", "nombre": "SAN JERONIMO", "departamento": "ANTIOQUIA", "lat": 6.4431, "lon": -75.7281},
    {"codigo": "05658", "nombre": "SAN JOSE DE LA MONTAÑA", "departamento": "ANTIOQUIA", "lat": 6.8503, "lon": -75.6786},
    {"codigo": "05659", "nombre": "SAN JUAN DE URABA", "departamento": "ANTIOQUIA", "lat": 8.7600, "lon": -76.5275},
    {"codigo": "05660", "nombre": "SAN LUIS", "departamento": "ANTIOQUIA", "lat": 6.0431, "lon": -74.9931},
    {"codigo": "05664", "nombre": "SAN PEDRO", "departamento": "ANTIOQUIA", "lat": 6.4592, "lon": -75.5575},
    {"codigo": "05665", "nombre": "SAN PEDRO DE URABA", "departamento": "ANTIOQUIA", "lat": 8.2792, "lon": -76.3789},
    {"codigo": "05667", "nombre": "SAN RAFAEL", "departamento": "ANTIOQUIA", "lat": 6.2933, "lon": -75.0258},
    {"codigo": "05670", "nombre": "SAN ROQUE", "departamento": "ANTIOQUIA", "lat": 6.4869, "lon": -75.0203},
    {"codigo": "05674", "nombre": "SAN VICENTE", "departamento": "ANTIOQUIA", "lat": 6.2811, "lon": -75.3328},
    {"codigo": "05679", "nombre": "SANTA BARBARA", "departamento": "ANTIOQUIA", "lat": 5.8742, "lon": -75.5664},
    {"codigo": "05686", "nombre": "SANTA ROSA DE OSOS", "departamento": "ANTIOQUIA", "lat": 6.6469, "lon": -75.4603},
    {"codigo": "05690", "nombre": "SANTO DOMINGO", "departamento": "ANTIOQUIA", "lat": 6.4719, "lon": -75.1633},
    {"codigo": "05697", "nombre": "EL SANTUARIO", "departamento": "ANTIOQUIA", "lat": 6.1378, "lon": -75.2647},
    {"codigo": "05736", "nombre": "SEGOVIA", "departamento": "ANTIOQUIA", "lat": 7.0789, "lon": -74.7028},
    {"codigo": "05756", "nombre": "SONSON", "departamento": "ANTIOQUIA", "lat": 5.7142, "lon": -75.3094},
    {"codigo": "05761", "nombre": "SOPETRAN", "departamento": "ANTIOQUIA", "lat": 6.5028, "lon": -75.7458},
    {"codigo": "05789", "nombre": "TAMESIS", "departamento": "ANTIOQUIA", "lat": 5.6628, "lon": -75.7128},
    {"codigo": "05790", "nombre": "TARAZA", "departamento": "ANTIOQUIA", "lat": 7.5867, "lon": -75.4014},
    {"codigo": "05792", "nombre": "TARSO", "departamento": "ANTIOQUIA", "lat": 5.8694, "lon": -75.8225},
    {"codigo": "05809", "nombre": "TITIRIBI", "departamento": "ANTIOQUIA", "lat": 6.0625, "lon": -75.7958},
    {"codigo": "05819", "nombre": "TOLEDO", "departamento": "ANTIOQUIA", "lat": 7.0136, "lon": -75.6917},
    {"codigo": "05837", "nombre": "TURBO", "departamento": "ANTIOQUIA", "lat": 8.0939, "lon": -76.7281},
    {"codigo": "05842", "nombre": "URAMITA", "departamento": "ANTIOQUIA", "lat": 6.8989, "lon": -76.1742},
    {"codigo": "05847", "nombre": "URRAO", "departamento": "ANTIOQUIA", "lat": 6.3169, "lon": -76.1331},
    {"codigo": "05854", "nombre": "VALDIVIA", "departamento": "ANTIOQUIA", "lat": 7.1656, "lon": -75.4392},
    {"codigo": "05856", "nombre": "VALPARAISO", "departamento": "ANTIOQUIA", "lat": 5.6147, "lon": -75.6244},
    {"codigo": "05858", "nombre": "VEGACHI", "departamento": "ANTIOQUIA", "lat": 6.7728, "lon": -74.7997},
    {"codigo": "05861", "nombre": "VENECIA", "departamento": "ANTIOQUIA", "lat": 5.9647, "lon": -75.7361},
    {"codigo": "05873", "nombre": "VIGIA DEL FUERTE", "departamento": "ANTIOQUIA", "lat": 6.5878, "lon": -76.8989},
    {"codigo": "05885", "nombre": "YALI", "departamento": "ANTIOQUIA", "lat": 6.6739, "lon": -74.8350},
    {"codigo": "05887", "nombre": "YARUMAL", "departamento": "ANTIOQUIA", "lat": 6.9633, "lon": -75.4172},
    {"codigo": "05890", "nombre": "YOLOMBO", "departamento": "ANTIOQUIA", "lat": 6.5969, "lon": -75.0119},
    {"codigo": "05893", "nombre": "YONDO", "departamento": "ANTIOQUIA", "lat": 7.0006, "lon": -73.9111},
    {"codigo": "05895", "nombre": "ZARAGOZA", "departamento": "ANTIOQUIA", "lat": 7.4886, "lon": -74.8678},
    # Capitals & main cities other departments
    {"codigo": "11001", "nombre": "BOGOTA", "departamento": "BOGOTA D.C.", "lat": 4.7110, "lon": -74.0721},
    {"codigo": "76001", "nombre": "CALI", "departamento": "VALLE DEL CAUCA", "lat": 3.4516, "lon": -76.5320},
    {"codigo": "08001", "nombre": "BARRANQUILLA", "departamento": "ATLANTICO", "lat": 10.9685, "lon": -74.7813},
    {"codigo": "13001", "nombre": "CARTAGENA", "departamento": "BOLIVAR", "lat": 10.3910, "lon": -75.4794},
    {"codigo": "68001", "nombre": "BUCARAMANGA", "departamento": "SANTANDER", "lat": 7.1193, "lon": -73.1227},
    {"codigo": "66001", "nombre": "PEREIRA", "departamento": "RISARALDA", "lat": 4.8133, "lon": -75.6961},
    {"codigo": "17001", "nombre": "MANIZALES", "departamento": "CALDAS", "lat": 5.0689, "lon": -75.5174},
    {"codigo": "73001", "nombre": "IBAGUE", "departamento": "TOLIMA", "lat": 4.4389, "lon": -75.2322},
    {"codigo": "63001", "nombre": "ARMENIA", "departamento": "QUINDIO", "lat": 4.5339, "lon": -75.6811},
    {"codigo": "41001", "nombre": "NEIVA", "departamento": "HUILA", "lat": 2.9273, "lon": -75.2819},
    {"codigo": "52001", "nombre": "PASTO", "departamento": "NARIÑO", "lat": 1.2136, "lon": -77.2811},
    {"codigo": "54001", "nombre": "CUCUTA", "departamento": "NORTE DE SANTANDER", "lat": 7.8939, "lon": -72.5078},
    {"codigo": "23001", "nombre": "MONTERIA", "departamento": "CORDOBA", "lat": 8.7479, "lon": -75.8814},
    {"codigo": "50001", "nombre": "VILLAVICENCIO", "departamento": "META", "lat": 4.1420, "lon": -73.6266},
    {"codigo": "47001", "nombre": "SANTA MARTA", "departamento": "MAGDALENA", "lat": 11.2408, "lon": -74.1990},
    {"codigo": "20001", "nombre": "VALLEDUPAR", "departamento": "CESAR", "lat": 10.4631, "lon": -73.2532},
    {"codigo": "44001", "nombre": "RIOHACHA", "departamento": "LA GUAJIRA", "lat": 11.5447, "lon": -72.9072},
    {"codigo": "70001", "nombre": "SINCELEJO", "departamento": "SUCRE", "lat": 9.3047, "lon": -75.3978},
    {"codigo": "19001", "nombre": "POPAYAN", "departamento": "CAUCA", "lat": 2.4448, "lon": -76.6147},
    {"codigo": "15001", "nombre": "TUNJA", "departamento": "BOYACA", "lat": 5.5353, "lon": -73.3678},
    {"codigo": "27001", "nombre": "QUIBDO", "departamento": "CHOCO", "lat": 5.6919, "lon": -76.6583},
    {"codigo": "18001", "nombre": "FLORENCIA", "departamento": "CAQUETA", "lat": 1.6144, "lon": -75.6062},
    {"codigo": "85001", "nombre": "YOPAL", "departamento": "CASANARE", "lat": 5.3389, "lon": -72.3956},
    {"codigo": "86001", "nombre": "MOCOA", "departamento": "PUTUMAYO", "lat": 1.1469, "lon": -76.6478},
    {"codigo": "97001", "nombre": "MITU", "departamento": "VAUPES", "lat": 1.2569, "lon": -70.2342},
    {"codigo": "91001", "nombre": "LETICIA", "departamento": "AMAZONAS", "lat": -4.2153, "lon": -69.9406},
    {"codigo": "94001", "nombre": "INIRIDA", "departamento": "GUAINIA", "lat": 3.8653, "lon": -67.9239},
    {"codigo": "88001", "nombre": "SAN ANDRES", "departamento": "SAN ANDRES", "lat": 12.5847, "lon": -81.7006},
    {"codigo": "99001", "nombre": "PUERTO CARREÑO", "departamento": "VICHADA", "lat": 6.1842, "lon": -67.4856},
    {"codigo": "95001", "nombre": "SAN JOSE DEL GUAVIARE", "departamento": "GUAVIARE", "lat": 2.5703, "lon": -72.6411},
    {"codigo": "25001", "nombre": "AGUA DE DIOS", "departamento": "CUNDINAMARCA", "lat": 4.3756, "lon": -74.6700},
    {"codigo": "81001", "nombre": "ARAUCA", "departamento": "ARAUCA", "lat": 7.0844, "lon": -70.7591},
]


def _normalize(s: str) -> str:
    import unicodedata
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


_BY_NAME = {_normalize(m["nombre"]): m for m in MUNICIPIOS}
_BY_CODE = {m["codigo"]: m for m in MUNICIPIOS}


def lookup(name: str = None, codigo: str = None):
    if codigo:
        m = _BY_CODE.get(str(codigo).zfill(5))
        if m:
            return m
    if name:
        n = _normalize(name)
        if n in _BY_NAME:
            return _BY_NAME[n]
        # fuzzy contains
        for k, v in _BY_NAME.items():
            if k and (k in n or n in k):
                return v
    return None


def list_all():
    return MUNICIPIOS
