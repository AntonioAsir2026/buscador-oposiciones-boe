"""Busca convocatorias informáticas en los sumarios oficiales del BOE.
Ejecutar: python actualizar.py
Solo usa librerías incluidas con Python 3.10 o superior.
"""

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

CARPETA = Path(__file__).parent
ARCHIVO = CARPETA / "datos.json"
API = "https://www.boe.es/datosabiertos/api/boe/sumario/"

# Palabras relacionadas con puestos de informática.
PALABRAS = (
    "informatic", "tecnologias de la informacion", "tecnologia de la informacion",
    "tecnologias de informacion", "tecnologia de informacion",
    "sistemas de informacion", "sistemas microinformaticos", "programador",
    "operador de sistemas", "tecnico tic", "auxiliar tic", "personal tic",
    "administrador de sistemas", "soporte informatico",
)

# Relación de provincias y sus comunidades, para filtrar los ayuntamientos.
PROVINCIAS = {
    "alava": "País Vasco", "araba": "País Vasco", "vizcaya": "País Vasco", "bizkaia": "País Vasco", "guipuzcoa": "País Vasco", "gipuzkoa": "País Vasco",
    "albacete": "Castilla-La Mancha", "ciudad real": "Castilla-La Mancha", "cuenca": "Castilla-La Mancha", "guadalajara": "Castilla-La Mancha", "toledo": "Castilla-La Mancha",
    "alicante": "Comunidad Valenciana", "alacant": "Comunidad Valenciana", "castellon": "Comunidad Valenciana", "castello": "Comunidad Valenciana", "valencia": "Comunidad Valenciana", "valencia/valencia": "Comunidad Valenciana",
    "almeria": "Andalucía", "cadiz": "Andalucía", "cordoba": "Andalucía", "granada": "Andalucía", "huelva": "Andalucía", "jaen": "Andalucía", "malaga": "Andalucía", "sevilla": "Andalucía",
    "asturias": "Asturias", "avila": "Castilla y León", "burgos": "Castilla y León", "leon": "Castilla y León", "palencia": "Castilla y León", "salamanca": "Castilla y León", "segovia": "Castilla y León", "soria": "Castilla y León", "valladolid": "Castilla y León", "zamora": "Castilla y León",
    "badajoz": "Extremadura", "caceres": "Extremadura", "barcelona": "Cataluña", "girona": "Cataluña", "gerona": "Cataluña", "lleida": "Cataluña", "lerida": "Cataluña", "tarragona": "Cataluña",
    "a coruna": "Galicia", "la coruna": "Galicia", "lugo": "Galicia", "ourense": "Galicia", "orense": "Galicia", "pontevedra": "Galicia",
    "huesca": "Aragón", "teruel": "Aragón", "zaragoza": "Aragón",
    "illes balears": "Islas Baleares", "islas baleares": "Islas Baleares", "baleares": "Islas Baleares",
    "las palmas": "Canarias", "santa cruz de tenerife": "Canarias",
    "la rioja": "La Rioja", "madrid": "Comunidad de Madrid", "murcia": "Región de Murcia", "navarra": "Navarra", "cantabria": "Cantabria", "ceuta": "Ceuta", "melilla": "Melilla",
}

REGIONES = {
    "Andalucía", "Aragón", "Asturias", "Islas Baleares", "Canarias", "Cantabria",
    "Castilla-La Mancha", "Castilla y León", "Cataluña", "Comunidad Valenciana",
    "Extremadura", "Galicia", "Comunidad de Madrid", "Región de Murcia", "Navarra",
    "País Vasco", "La Rioja", "Ceuta", "Melilla",
}


def normalizar(texto):
    """Quita tildes y pasa el texto a minúsculas."""
    texto = unicodedata.normalize("NFD", texto or "")
    return "".join(letra for letra in texto if unicodedata.category(letra) != "Mn").lower()


def etiqueta(elemento):
    """Etiqueta de XML aunque tenga espacios de nombres."""
    return elemento.tag.rsplit("}", 1)[-1].lower()


def contenido(elemento, nombre):
    """Obtiene el texto del primer campo con ese nombre dentro de un item."""
    for hijo in elemento.iter():
        if etiqueta(hijo) == nombre:
            return (hijo.text or "").strip()
    return ""


def descargar(url):
    """Descarga solo recursos oficiales del BOE."""
    destino = urllib.parse.urlparse(url)
    if destino.scheme != "https" or destino.hostname not in ("www.boe.es", "boe.es"):
        raise ValueError("Dirección no perteneciente al BOE")
    peticion = urllib.request.Request(url, headers={
        "User-Agent": "ProyectoASIR-ConsultaBOE/1.0",
        "Accept": "application/xml",
    })
    with urllib.request.urlopen(peticion, timeout=20) as respuesta:
        return respuesta.read()


def es_informatica(texto):
    texto = normalizar(texto)
    return any(palabra in texto for palabra in PALABRAS)


def comunidad(titulo, departamento):
    """Averigua la comunidad por la provincia del título, si aparece."""
    # Muchos anuncios municipales terminan en (Madrid), (Sevilla), etc.
    for lugar in reversed(re.findall(r"\(([^)]+)\)", titulo)):
        # Ejemplo: Almassora (Castellón/Castelló).
        for provincia in re.split(r"[/,]", lugar):
            encontrada = PROVINCIAS.get(normalizar(provincia).strip())
            if encontrada:
                return encontrada

    texto = normalizar(titulo + " " + departamento)
    # A veces el BOE solo indica «Ayuntamiento de Badajoz», sin provincia.
    if any(nombre in texto for nombre in ("ayuntamiento", "diputacion provincial")):
        for provincia in sorted(PROVINCIAS, key=len, reverse=True):
            if re.search(r"\b" + re.escape(provincia) + r"\b", texto):
                return PROVINCIAS[provincia]
    for region in sorted(REGIONES, key=len, reverse=True):
        if normalizar(region) in texto:
            return region

    # No suponer la comunidad sin información suficiente.
    if "administracion local" in normalizar(departamento) or "ayuntamiento" in texto:
        return "Sin identificar"
    return "Estado / ámbito general"


def es_convocatoria(titulo, departamento):
    """Se queda solo con anuncios relacionados con selección de personal."""
    texto = normalizar(titulo)

    # Estos anuncios no son ofertas de empleo público.
    descartados = (
        "licitacion", "formalizacion de contrato", "adjudicacion de contrato",
        "suministro de", "contratacion de servicios", "plan de estudios",
        "titulo universitario", "extracto de titulo", "subvencion", "enajenacion",
        "contratos de servicios", "convenio de colaboracion",
    )
    if any(palabra in texto for palabra in descartados):
        return False

    # La categoría (universidad, ayuntamiento...) no basta para ser una oferta.
    palabras_empleo = (
        "convocatoria", "convocan", "convoca", "proveer", "plaza", "plazas",
        "pruebas selectivas", "proceso selectivo", "procesos selectivos",
        "oposicion", "bolsa de empleo", "bolsa de trabajo", "ingreso libre",
        "provision de puestos", "seleccion de personal",
    )
    return any(palabra in texto for palabra in palabras_empleo)


def es_puesto_informatico(texto):
    """Comprueba que la informática forma parte del puesto convocado."""
    texto = normalizar(texto)
    nombres_puesto = (
        "plaza", "plazas", "puesto", "puestos", "tecnico", "tecnica",
        "auxiliar", "cuerpo", "escala", "programador", "administrador",
        "operador", "bolsa",
    )
    for frase in re.split(r"[.;!?\n]+", texto):
        for palabra in PALABRAS:
            inicio = 0
            while True:
                posicion = frase.find(palabra, inicio)
                if posicion == -1:
                    break
                entorno = frase[max(0, posicion - 130):posicion + len(palabra) + 130]
                if any(re.search(r"\b" + re.escape(p) + r"\b", entorno) for p in nombres_puesto):
                    return True
                inicio = posicion + len(palabra)
    return False


def texto_de_documento(xml):
    """Extrae el texto del documento XML del BOE."""
    raiz = ET.fromstring(xml)
    for elemento in raiz.iter():
        if etiqueta(elemento) == "texto":
            return " ".join(elemento.itertext())
    return " ".join(raiz.itertext())


def clasificar_acceso(texto):
    """Diferencia convocatorias de acceso libre y promoción interna."""
    texto = normalizar(texto)
    libre = any(frase in texto for frase in (
        "turno libre", "acceso libre", "turno de acceso libre", "ingreso libre"
    ))
    interna = "promocion interna" in texto
    if libre and interna:
        return "Libre e interna"
    if interna:
        return "Promoción interna"
    if libre:
        return "Turno libre"
    return "No indicado"


def categoria(titulo, departamento):
    texto = normalizar(titulo + " " + departamento)
    if "ayuntamiento" in texto or "administracion local" in texto:
        return "Ayuntamiento / Administración local"
    if "universidad" in texto:
        return "Universidad"
    if "comunidad autonoma" in texto:
        return "Comunidad autónoma"
    return "Estado / otras administraciones"


def recoger_items(elemento, departamento=""):
    """Recorre el XML conservando el departamento de cada anuncio."""
    nombre = etiqueta(elemento)
    if nombre in ("departamento", "organismo"):
        departamento = (elemento.attrib.get("nombre") or contenido_directo(elemento, "nombre") or departamento)
    if nombre == "item":
        yield elemento, departamento
    else:
        for hijo in elemento:
            yield from recoger_items(hijo, departamento)


def contenido_directo(elemento, nombre):
    for hijo in elemento:
        if etiqueta(hijo) == nombre:
            return (hijo.text or "").strip()
    return ""


def detectar(xml, fecha, consultar_detalle=False):
    raiz = ET.fromstring(xml)
    salida = []
    consultas_de_detalle = 0
    for item, departamento in recoger_items(raiz):
        titulo = contenido(item, "titulo")
        identificador = contenido(item, "identificador")
        if not titulo or not identificador or not identificador.startswith("BOE-"):
            continue
        if not es_convocatoria(titulo, departamento):
            continue
        encontrado = es_informatica(titulo)
        clase = categoria(titulo, departamento)
        acceso = "No indicado"

        # Leemos también el documento cuando está disponible: algunos
        # títulos no indican ni el puesto ni el turno de acceso.
        if consultar_detalle and consultas_de_detalle < 30 and (
            encontrado or "Administración local" in clase
        ):
            url_xml = contenido(item, "url_xml")
            if url_xml:
                consultas_de_detalle += 1
                try:
                    cuerpo = texto_de_documento(descargar(url_xml))
                    acceso = clasificar_acceso(cuerpo)
                    if not encontrado:
                        encontrado = es_puesto_informatico(cuerpo)
                    time.sleep(0.1)
                except (urllib.error.URLError, ValueError, TimeoutError, ET.ParseError):
                    pass
        if not encontrado:
            continue

        # Cuando el título incluye el turno, también sirve para clasificarlo.
        if acceso == "No indicado":
            acceso = clasificar_acceso(titulo)

        pdf = contenido(item, "url_pdf")
        if pdf and not pdf.startswith("https://www.boe.es/") and not pdf.startswith("https://boe.es/"):
            pdf = ""
        salida.append({
            "id": identificador,
            "titulo": titulo,
            "fecha": fecha.isoformat(),
            "comunidad": comunidad(titulo, departamento),
            "organismo": clase,
            "acceso": acceso,
            "boe": "https://www.boe.es/buscar/doc.php?id=" + urllib.parse.quote(identificador),
            "pdf": pdf,
        })
    return salida


def actualizar(dias=14):
    if ARCHIVO.exists():
        try:
            datos_anteriores = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            datos_anteriores = {}
    else:
        datos_anteriores = {}
    registros = {
        x["id"]: x for x in datos_anteriores.get("resultados", [])
        if x.get("id") and es_convocatoria(x.get("titulo", ""), x.get("organismo", ""))
    }
    hoy = date.today()
    completados = 0
    errores = []
    for diferencia in range(dias):
        dia = hoy - timedelta(days=diferencia)
        url = API + dia.strftime("%Y%m%d")
        try:
            xml = descargar(url)
            nuevos = detectar(xml, dia, consultar_detalle=True)
            for registro in nuevos:
                registros[registro["id"]] = registro
            completados += 1
            print(f"{dia}: {len(nuevos)} resultados de informática")
        except urllib.error.HTTPError as error:
            # Los domingos normalmente no se publica el BOE.
            if error.code != 404:
                errores.append(f"{dia}: HTTP {error.code}")
        except (urllib.error.URLError, ET.ParseError, TimeoutError, ValueError) as error:
            errores.append(f"{dia}: {error}")
    if completados == 0:
        raise RuntimeError("No se ha podido leer el BOE. Comprueba Internet o vuelve a intentarlo.")
    ordenados = sorted(registros.values(), key=lambda x: (x["fecha"], x["id"]), reverse=True)
    resultado = {
        "actualizado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dias_consultados": completados,
        "errores": errores,
        "resultados": ordenados[:1000],
    }
    temporal = ARCHIVO.with_suffix(".tmp")
    temporal.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ARCHIVO)
    print(f"Guardados {len(ordenados[:1000])} anuncios en datos.json")
    if errores:
        print("Algunos días no se pudieron consultar:", "; ".join(errores))


if __name__ == "__main__":
    actualizar()
