// Código JavaScript básico. Filtra y muestra los anuncios del BOE.
const listaComunidades = [
  "Andalucía", "Aragón", "Asturias", "Islas Baleares", "Canarias",
  "Cantabria", "Castilla-La Mancha", "Castilla y León", "Cataluña",
  "Comunidad Valenciana", "Extremadura", "Galicia", "Comunidad de Madrid",
  "Región de Murcia", "Navarra", "País Vasco", "La Rioja", "Ceuta", "Melilla",
  "Estado / ámbito general", "Sin identificar"
];
let ofertas = [];

const zonaComunidades = document.getElementById("comunidades");
const resultados = document.getElementById("resultados");
const buscar = document.getElementById("buscar");
const organismo = document.getElementById("organismo");
const acceso = document.getElementById("acceso");

// Dibujamos los filtros con casillas: se pueden marcar varias comunidades.
listaComunidades.forEach((nombre, indice) => {
  const etiqueta = document.createElement("label");
  const casilla = document.createElement("input");
  casilla.type = "checkbox";
  casilla.value = nombre;
  casilla.id = `comunidad-${indice}`;
  casilla.addEventListener("change", mostrar);
  etiqueta.append(casilla, document.createTextNode(nombre));
  zonaComunidades.append(etiqueta);
});

function normalizar(texto) {
  return (texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function mostrar() {
  const seleccionadas = Array.from(zonaComunidades.querySelectorAll("input:checked"), x => x.value);
  const palabra = normalizar(buscar.value.trim());
  const tipo = organismo.value;
  const turno = acceso.value;
  const filtradas = ofertas.filter(oferta => {
    const coincideTexto = normalizar(oferta.titulo + " " + oferta.organismo).includes(palabra);
    const coincideComunidad = seleccionadas.length === 0 || seleccionadas.includes(oferta.comunidad);
    const coincideTipo = !tipo || oferta.organismo.includes(tipo);
    const coincideTurno = !turno || (oferta.acceso || "No indicado") === turno;
    return coincideTexto && coincideComunidad && coincideTipo && coincideTurno;
  });
  document.getElementById("contador").textContent = `(${filtradas.length})`;
  resultados.replaceChildren();
  if (filtradas.length === 0) {
    const aviso = document.createElement("p");
    aviso.className = "vacio";
    aviso.textContent = ofertas.length === 0
      ? "Todavía no hay datos. Primero hay que ejecutar actualizar.py para leer el BOE."
      : "No hay resultados con esos filtros. Prueba a quitar alguno.";
    resultados.append(aviso);
    return;
  }
  for (const oferta of filtradas) {
    const articulo = document.createElement("article");
    articulo.className = "oferta";
    const titulo = document.createElement("h3");
    titulo.textContent = oferta.titulo; // textContent evita interpretar HTML externo.
    const detalle = document.createElement("p");
    detalle.textContent = `${oferta.fecha} · ${oferta.comunidad} · ${oferta.organismo} · ${oferta.acceso || "No indicado"}`;
    const enlace = document.createElement("a");
    enlace.textContent = "Ver anuncio en BOE";
    enlace.href = oferta.boe;
    enlace.target = "_blank";
    enlace.rel = "noopener noreferrer";
    articulo.append(titulo, detalle, enlace);
    if (oferta.pdf) {
      const pdf = document.createElement("a");
      pdf.href = oferta.pdf;
      pdf.textContent = "Abrir PDF";
      pdf.target = "_blank";
      pdf.rel = "noopener noreferrer";
      articulo.append(pdf);
    }
    resultados.append(articulo);
  }
}

buscar.addEventListener("input", mostrar);
organismo.addEventListener("change", mostrar);
acceso.addEventListener("change", mostrar);
document.getElementById("todas").addEventListener("click", () => {
  zonaComunidades.querySelectorAll("input").forEach(c => { c.checked = false; });
  buscar.value = "";
  organismo.value = "";
  acceso.value = "";
  mostrar();
});

// Cargamos los datos que ha guardado el programa Python.
fetch("datos.json", {cache: "no-store"})
  .then(respuesta => {
    if (!respuesta.ok) throw new Error("No se encuentra datos.json");
    return respuesta.json();
  })
  .then(datos => {
    ofertas = datos.resultados || [];
    const fecha = datos.actualizado ? new Date(datos.actualizado).toLocaleString("es-ES") : "sin actualizar";
    const problemas = (datos.errores || []).length;
    document.getElementById("actualizacion").textContent =
      `Última actualización: ${fecha}. ${problemas ? `Aviso: ${problemas} días no se pudieron consultar.` : ""}`;
    mostrar();
  })
  .catch(error => {
    document.getElementById("actualizacion").textContent = "No se han podido cargar los datos.";
    resultados.textContent = "Abre la web mediante el servidor local, no haciendo doble clic en index.html.";
    console.error(error);
  });
