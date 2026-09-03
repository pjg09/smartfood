/* Comportamiento del armazón: el tema y las dos barras (DT-23).
 *
 * Todo lo que hay aquí es cromo. **Ninguna regla de negocio vive en el
 * navegador**: el saldo, los permisos y las restricciones se deciden en el
 * servidor (`DT-11`, `DT-15`), y una barra lateral que se colapsa no cambia lo
 * que alguien puede hacer — `INV-4` se sostiene en la capa de datos, no
 * escondiendo botones.
 *
 * Sin framework y sin construcción: el stack es Django + HTMX (`DT-16`) y este
 * fichero se sirve tal cual. Son ~100 líneas; una dependencia para esto costaría
 * más de lo que resuelve.
 */

(function () {
  "use strict";

  /* --- Tema -------------------------------------------------------------
   *
   * Tres estados, no dos: claro, oscuro y «el del sistema». El tercero es el
   * que trae por defecto y el que la mayoría no toca nunca.
   *
   * Lo que EVITA el parpadeo blanco al cargar no está aquí: es el script inline
   * de `base.html`, que corre antes de pintar. Esto solo atiende al selector.
   */
  var CLAVE_TEMA = "smartfood:tema";

  function aplicarTema(valor) {
    if (valor === "claro" || valor === "oscuro") {
      document.documentElement.setAttribute("data-tema", valor);
      localStorage.setItem(CLAVE_TEMA, valor);
    } else {
      // «Sistema» es la AUSENCIA de atributo, no un tercer valor: así la media
      // query de `prefers-color-scheme` vuelve a mandar sola.
      document.documentElement.removeAttribute("data-tema");
      localStorage.removeItem(CLAVE_TEMA);
    }
  }

  function temaGuardado() {
    var valor = localStorage.getItem(CLAVE_TEMA);
    return valor === "claro" || valor === "oscuro" ? valor : "sistema";
  }

  function montarSelectorDeTema() {
    var selector = document.querySelector("[data-selector-de-tema]");
    if (selector === null) return;

    selector.value = temaGuardado();
    selector.addEventListener("change", function () {
      aplicarTema(selector.value);
    });
  }

  /* --- Barra lateral ----------------------------------------------------
   *
   * Desde tablet la barra es fija y se colapsa a iconos; en móvil no cabe y se
   * abre como un cajón sobre el contenido. El MISMO botón hace las dos cosas
   * según el ancho, igual que la barra superior de la que cuelga.
   *
   * El estado vive en un atributo del elemento RAÍZ, no en una clase del
   * armazón: así lo puede poner el script inline de `base.html` antes de pintar
   * —si no, la barra aparece desplegada y se cierra de golpe a la vista— y la
   * variante `colapsada:` de la hoja de estilos alcanza a cualquier elemento sin
   * tener que encadenar `group`.
   *
   * Se recuerda porque es una preferencia de quien trabaja aquí todos los días,
   * no un estado de la pantalla.
   */
  var CLAVE_BARRA = "smartfood:barra-colapsada";
  var ATRIBUTO_BARRA = "data-barra-colapsada";

  function montarBarra() {
    var boton = document.querySelector("[data-alternar-barra]");
    if (boton === null) return;

    var raiz = document.documentElement;
    var cajon = document.querySelector("[data-cajon]");

    function colapsada() {
      return raiz.getAttribute(ATRIBUTO_BARRA) === "si";
    }

    function abrirCajon(abierto) {
      if (cajon === null) return;
      cajon.hidden = !abierto;
      // Mientras el cajón tapa la pantalla no se hace scroll por detrás.
      document.body.style.overflow = abierto ? "hidden" : "";
    }

    boton.addEventListener("click", function () {
      // 48rem es `--breakpoint-tablet`. Es el mismo umbral que usa la hoja de
      // estilos para pasar del cajón a la barra fija: si los dos se separan,
      // el botón abre el cajón en un ancho donde la barra ya es visible.
      if (window.matchMedia("(min-width: 48rem)").matches) {
        var siguiente = colapsada() ? "no" : "si";
        raiz.setAttribute(ATRIBUTO_BARRA, siguiente);
        localStorage.setItem(CLAVE_BARRA, siguiente);
        boton.setAttribute("aria-expanded", siguiente === "si" ? "false" : "true");
      } else {
        abrirCajon(true);
      }
    });

    document.querySelectorAll("[data-cerrar-cajon]").forEach(function (elemento) {
      elemento.addEventListener("click", function () {
        abrirCajon(false);
      });
    });

    // Escape cierra el cajón. Sin esto, en un teléfono con teclado físico o con
    // un lector de pantalla no hay forma de salir sin buscar la equis.
    document.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape") abrirCajon(false);
    });
  }

  /* --- Cabecera de la portada -------------------------------------------
   *
   * Transparente mientras se está arriba del todo, opaca al bajar. Se decide
   * con un `IntersectionObserver` sobre un centinela de un píxel, no
   * escuchando `scroll`: ese evento se dispara decenas de veces por segundo
   * para responder a una pregunta que solo tiene dos respuestas.
   *
   * **Solo se activa si la pantalla declara que debajo hay héroe.** Sobre el
   * fondo claro de una página normal, la tinta clara de la cabecera
   * desaparecería. Y si este fichero no llega a ejecutarse, la cabecera se
   * queda opaca, que es el estado que nunca se ve mal.
   */
  function montarCabeceraPublica() {
    var cabecera = document.querySelector("[data-cabecera-publica]");
    var centinela = document.querySelector("[data-centinela-cabecera]");
    if (cabecera === null || centinela === null) return;
    if (cabecera.getAttribute("data-sobre-heroe") !== "si") return;

    cabecera.setAttribute("data-arriba", "si");

    new IntersectionObserver(function (entradas) {
      var visible = entradas[0] !== undefined ? entradas[0].isIntersecting : true;
      cabecera.setAttribute("data-arriba", visible ? "si" : "no");
    }).observe(centinela);
  }

  /* --- Selector de estudiante (`TT-29`) ---------------------------------
   *
   * Marca cuál está elegido. La vista devuelve el DETALLE, no el selector
   * (`DT-16`: un fragmento, nunca una página), así que el botón pulsado no se
   * vuelve a pintar solo y sin esto los chips se quedan todos apagados.
   *
   * **Es cromo y nada más.** Qué estudiante puede ver quién lo decide el
   * selector de datos del servidor, que responde 404 para uno que no esté a
   * cargo aunque el chip se marque a la fuerza desde la consola (`DT-15`).
   */
  function montarSelectorDeEstudiante() {
    var grupo = document.querySelector("[data-selector-estudiante]");
    if (grupo === null) return;

    grupo.addEventListener("click", function (evento) {
      var pulsado = evento.target.closest("button");
      if (pulsado === null || !grupo.contains(pulsado)) return;

      grupo.querySelectorAll("button").forEach(function (boton) {
        boton.removeAttribute("aria-current");
      });
      pulsado.setAttribute("aria-current", "true");
    });
  }

  /* HTMX intercambia fragmentos, no páginas (`DT-16`), así que el armazón no se
   * vuelve a construir: basta con montarlo una vez. */
  document.addEventListener("DOMContentLoaded", function () {
    montarSelectorDeTema();
    montarBarra();
    montarCabeceraPublica();
    montarSelectorDeEstudiante();
  });
})();
