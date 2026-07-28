// op_seg_view.js
// -----------------------------------------------------------------------------
// OBJETIVO
// Monta e renderiza dinamicamente os alertas SSMA na tela usando df (JSON)
// injetado pelo backend via Jinja (Flask).
// -----------------------------------------------------------------------------

document.title = "Alerta SSMA - " + {{ day | tojson }} + "/" + {{ month | tojson }} + "/" + {{ year | tojson }};

removeNav();

// ✅ lista de datas marcadas (YYYY-MM-DD) vinda do backend (SOMENTE DO MÊS ATUAL)
var availableDates = {{ available_dates | default([]) | tojson }};

function pad2(n) {
  return String(n).padStart(2, "0");
}

function currentKey() {
  var d = pad2(Number({{ day | tojson }}));
  var m = pad2(Number({{ month | tojson }}));
  var y = String(Number({{ year | tojson }}));
  return `${y}-${m}-${d}`;
}

function goToKey(key) {
  var parts = key.split("-");
  var y = parts[0];
  var m = parseInt(parts[1], 10);
  var d = parseInt(parts[2], 10);

  // ✅ URL correta com "&"
  var url = "/op/ssma/view?day=" + d + "&month=" + m + "&year=" + y;

  // preserva filtro de unidade se existir
  var cur = new URL(window.location.href);
  if (cur.searchParams.has("state")) {
    url += "&state=" + encodeURIComponent(cur.searchParams.get("state"));
  }

  window.location = url;
}

// ✅ Navegação por dias marcados (agora também troca de mês/ano quando chegar no limite)
function changeLoc(acao) {
  if (acao === "download") {
    window.print();
    return;
  }

  if (!Array.isArray(availableDates) || availableDates.length === 0) {
    console.warn("availableDates vazio: sem dias marcados para navegar.");
    return;
  }

  var key = currentKey();
  var idx = availableDates.indexOf(key);

  // se a data atual não estiver na lista, pega a primeira >= ela
  if (idx === -1) {
    idx = availableDates.findIndex(d => d >= key);
    if (idx === -1) idx = availableDates.length - 1;
  }

  // preserva filtro de unidade se existir
  var cur = new URL(window.location.href);
  var state = cur.searchParams.has("state") ? cur.searchParams.get("state") : null;

  if (acao === "voltar") {
    // ✅ ainda tem anterior no mesmo mês
    if (idx > 0) {
      goToKey(availableDates[idx - 1]);
      return;
    }

    // ✅ está no primeiro marcado do mês => pedir anterior global (pode mudar mês/ano)
    var urlPrev = "/op/ssma/view?day=" + Number({{ day | tojson }}) +
                  "&month=" + Number({{ month | tojson }}) +
                  "&year=" + Number({{ year | tojson }}) +
                  "&nav=prev";
    if (state) urlPrev += "&state=" + encodeURIComponent(state);
    window.location = urlPrev;
    return;
  }

  if (acao === "prox") {
    // ✅ ainda tem próximo no mesmo mês
    if (idx < availableDates.length - 1) {
      goToKey(availableDates[idx + 1]);
      return;
    }

    // ✅ está no último marcado do mês => pedir próximo global (pode mudar mês/ano)
    var urlNext = "/op/ssma/view?day=" + Number({{ day | tojson }}) +
                  "&month=" + Number({{ month | tojson }}) +
                  "&year=" + Number({{ year | tojson }}) +
                  "&nav=next";
    if (state) urlNext += "&state=" + encodeURIComponent(state);
    window.location = urlNext;
    return;
  }

  window.print();
}

// -----------------------------------------------------------------------------
// Render
// -----------------------------------------------------------------------------

function classify(dano1, dano2, envolvido) {
  var not = [
    "Arranhão/Escoriação",
    "Corte/enfermidade leve",
    "Fratura leve de ossos - dedos das mãos/dedos dos pés",
    "Nenhum - sem lesão"
  ];

  var sif = not.includes(dano1) ? 0 : 1;
  var psif = not.includes(dano2) ? 0 : 1;

  var isFuncionario = (envolvido === "Funcionário" || envolvido === 1 || envolvido === "1");

  var clf = "red";
  var final = "";

  if (isFuncionario) {
    if (sif === 1 && psif === 1) final = "SIF & PSIF envolvendo funcionário";
    else if (psif === 1) final = "PSIF envolvendo funcionário";
    else if (sif === 1) final = "SIF envolvendo funcionário";
    else { final = "Não classificado como SIF ou PSIF"; clf = "green"; }
  } else {
    if (sif === 1 && psif === 1) final = "SIF & PSIF envolvendo terceiro";
    else if (psif === 1) final = "PSIF envolvendo terceiro";
    else if (sif === 1) final = "SIF envolvendo terceiro";
    else { final = "Não classificado como SIF ou PSIF"; clf = "green"; }
  }

  return [final, clf];
}

function safeJsonParse(value, fallback) {
  try {
    if (Array.isArray(value)) return value;
    if (typeof value === "object" && value !== null) return value;
    return JSON.parse(value);
  } catch (e) {
    return fallback;
  }
}

function loadPage() {
  // backend manda df.to_json() (string) => parse
  var df = JSON.parse({{ df | tojson }});

  // evita quebrar se df vier vazio
  if (!df || !df["id"] || Object.keys(df["id"]).length === 0) {
    console.warn("DF vazio: nada para renderizar.");
    return;
  }

  var val = Object.keys(df["id"]).length;

  var eventos = [
    "Acidente com perda de tempo",
    "Acidente sem perda de tempo",
    "Incidente de risco crítico",
    "Acidente com dano material",
    "Acidente com dano ambiental",
    "Incidente com risco potencial"
  ];

  var riscos = [
    "Armazenamento de Materiais",
    "Cargas Suspensas",
    "Combustíveis e Inflamáveis",
    "Energias Perigosas",
    "Espaço Confinado",
    "Explosão e Incêndio",
    "Máquinas e Equipamentos",
    "Metal Líquido",
    "Subestação",
    "Testes Críticos",
    "Trabalho em Altura",
    "Veículos Industriais"
  ];

  for (let i = 0; i < val; i++) {
    var event_check = [];
    var risk_check = [];

    var sif_psif = classify(df["realDamage"][i], df["potencialDamage"][i], df["involved"][i]);

    var event_list = safeJsonParse((df["event"][i] || "[]"), []);
    var class_list = safeJsonParse((df["class"][i] || "[]"), []);

    var event_list_lc = event_list.map(x => (x || "").toLowerCase());
    var class_list_lc = class_list.map(x => (x || "").toLowerCase());

    for (let k = 0; k < eventos.length; k++) {
      event_check.push(event_list_lc.includes(eventos[k].toLowerCase()) ? "1" : "0");
    }

    for (let k = 0; k < riscos.length; k++) {
      risk_check.push(class_list_lc.includes(riscos[k].toLowerCase()) ? "1" : "0");
    }

    // cabeçalho
    var id = "cross_square_4";
    if (["Acidente", "Acidente com Afastamento"].includes(df["definition"][i])) id = "cross_square_0";
    else if (df["definition"][i] === "Acidente sem Afastamento") id = "cross_square_1";
    else if (df["definition"][i] === "Atendimento Ambulatorial") id = "cross_square_2";
    else if (df["definition"][i] === "Registro de Incidente") id = "cross_square_3";
    else if (df["definition"][i] === "Em Análise") id = "cross_square_4";
    else if (df["definition"][i] === "Incidente Ambiental") id = "cross_square_5";

    if (id === "cross_square_0") df["definition"][i] = "Acidente com perda de tempo";
    else if (id === "cross_square_1") df["definition"][i] = "Acidente sem perda de tempo";
    else if (id === "cross_square_2") df["definition"][i] = "Atendimento Ambulatorial";
    else if (id === "cross_square_3") df["definition"][i] = "Incidente de segurança";
    else if (id === "cross_square_4") df["definition"][i] = "Em Análise";
    else if (id === "cross_square_5") df["definition"][i] = "Incidente Ambiental";

    // hora HH:MM (com proteção)
    var hora = "";
    try {
      var rawDate = (df["date"][i] || "");
      if (rawDate.includes(" ")) {
        var t = rawDate.split(" ")[1];
        if (t && t.includes(":")) hora = t.split(":")[0] + ":" + t.split(":")[1];
      }
    } catch (e) { hora = ""; }

    document.getElementById("seg_content").innerHTML += `
      <div class="seg_alert">
        <div class="seg_alert_title_wrap ${id}">
          <img class="seg_logo" src="/static/images/new_jost_logo.jpg"/>
          <p class="seg_alert_title">Alerta SSMA ${df["unit"][i]} - Nº ${df["id"][i]} Geral</p>
          <p class="seg_alert_desc"><b><i>${df["definition"][i]}</i></b> || Saúde, Segurança e Meio Ambiente</p>
        </div>

        <div class="seg_alert_subnav_wrap">
          <p class="seg_alert_subnav"><span style="font-weight:bold">Planta Industrial:</span> JOST Sistemas Automotivos Ltda.</p>
          <p class="seg_alert_subnav">||</p>
          <p class="seg_alert_subnav" style="font-weight:bold">{{ day }} / {{ month }} / {{ year }}</p>
        </div>

        <div class="seg_event_wrap">
          <p class="seg_event_title">Evento</p><div style="height:1vh;"></div>
          <div class="seg_event_topic_${event_check[0]}">Acidente com perda de tempo</div>
          <div class="seg_event_topic_${event_check[1]}">Acidente sem perda de tempo</div>
          <div class="seg_event_topic_${event_check[2]}">Incidente de risco crítico</div>
          <div class="seg_event_topic_${event_check[3]}">Incidente com dano material</div>
          <div class="seg_event_topic_${event_check[4]}">Incidente com dano ambiental</div>
          <div class="seg_event_topic_${event_check[5]}">Incidente com risco potencial</div>
        </div>

        <div class="seg_event_wrap" style="text-align:center">
          <p class="seg_event_title">Classificação Riscos Críticos</p><div style="height:1vh;"></div>
          ${riscos.map((r, idx2) => `<div class="seg_class_topic_${risk_check[idx2]}"><p>${r}</p></div>`).join("")}
        </div>

        <div class="seg_event_wrap" id="sif_psif">
          <p class="seg_event_title">Classificação SIF & PSIF</p>
          <div class="seg_event_wrap" id="sif_psif_status_${sif_psif[1]}">
            <p class="sif_psif">${sif_psif[0]}</p>
          </div>
        </div>

        <div class="seg_event_wrap" id="dados">
          <p class="seg_event_title">Dados da Ocorrência</p>
          <div class="seg_event_topic_0"><b>Setor: </b>${df["sector"][i]}</div>
          <div class="seg_event_topic_0"><b>Equipamento: </b>${df["equip"][i]}</div>
          <div class="seg_event_topic_0"><b>Local: </b>${df["local"][i]}</div>
          <div class="seg_event_topic_0"><b>Gerente: </b>${df["manager"][i]}</div>
          <div class="seg_event_topic_0"><b>Coordenador: </b>${df["coord"][i]}</div>
          <div class="seg_event_topic_0"><b>Contato SSMA: </b>${df["userContact"][i]}</div>
          <div class="seg_event_topic_0"><b>Ramal SSMA: </b>${df["ramalContact"][i]}</div>
          <div class="seg_event_topic_0"><b>Data: </b>{{ day }} / {{ month }} / {{ year }}</div>
          <div class="seg_event_topic_0"><b>Horário: </b>${hora}</div>
        </div>

        <div class="seg_big_wrap">
          <div class="seg_big_title">Descrição:</div>
          <div class="seg_big_field">${df["description"][i]}</div>
        </div>

        <div class="seg_big_wrap">
          <div class="seg_big_title">Causa raiz:</div>
          <div class="seg_big_field">${df["rootCause"][i]}</div>
        </div>

        <div class="seg_big_wrap">
          <div class="seg_big_title">Condições gerais do acidentado:</div>
          <div class="seg_big_field">${df["generalCondiction"][i]}</div>
        </div>

        <div class="seg_big_wrap">
          <div class="seg_big_title">Ações de contenção:</div>
          <div class="seg_big_field">${df["containment"][i]}</div>
        </div>

        <div class="seg_big_wrap">
          <div class="seg_big_title">Ações de correção:</div>
          <div class="seg_big_field">${df["solution"][i]}</div>
        </div>
      </div>
    `;

    // -----------------------------
    // Fotos
    // -----------------------------
    var images_list = safeJsonParse((df["images"][i] || "[]"), []);

    if (Array.isArray(images_list) && images_list.length > 0) {
      var pics = `
        <div class="seg_alert_pics">
          <div class="seg_alert_title_wrap ${id}">
            <img class="seg_logo" src="/static/images/new_jost_logo.jpg"/>
            <p class="seg_alert_title">Alerta SSMA ${df["unit"][i]} - Nº ${df["id"][i]} Geral</p>
            <p class="seg_alert_desc"><b><i>${df["definition"][i]}</i></b> || Saúde, Segurança e Meio Ambiente</p>
          </div>

          <div class="seg_alert_subnav_wrap">
            <p class="seg_alert_subnav"><b>Fotos e Danos - Ocorrência Nº ${df["id"][i]}</b></p>
            <p class="seg_alert_subnav">||</p>
            <p class="seg_alert_subnav" style="font-weight:bold">{{ day }} / {{ month }} / {{ year }}</p>
          </div>

          <div class="seg_pictures">
            <p class="seg_pics_topic"><b>Dano Real:</b> ${df["realDamage"][i]}</p>
            <p class="seg_pics_topic"><b>Dano Potencial:</b> ${df["potencialDamage"][i]}</p>
      `;

      for (let k = 0; k < images_list.length; k++) {
        var src = encodeURIComponent(images_list[k]);
        pics += `
          <p class="seg_pic_lbl">
            Foto ${k + 1}
            <img class="seg_img" src="/static/uploads/operation/ssma/${df["id"][i]}/${src}"/>
          </p>
        `;
      }

      pics += `
          </div>
        </div>
      `;

      document.getElementById("seg_content").innerHTML += pics;
    }
  }s
}

loadPage();