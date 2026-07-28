// Dados seguros (tojson + parse)
var df = JSON.parse({{ dataframe | tojson }});
var df_plan = JSON.parse({{ df_plan | tojson }});
var df_result = JSON.parse({{ df_result | tojson }});

var idReq = df['deviationId'][0];

/** Aplica cor padrão por status no header */
function colorForStatus(st){
    // 0 aguardando (amarelo), 1 aprovado/5 andamento (verde), 2 recusado/6 vencido (vermelho), 3 cancelado/4 finalizado (cinza)
    if (st === 0) return "rgba(242, 202, 2, 0.7)";
    if (st === 1 || st === 5) return "rgba(89, 184, 26, 0.7)";
    if (st === 2 || st === 6) return "rgba(201, 35, 24, 0.7)";
    return "rgba(128, 128, 128, 0.7)"; // 3 e 4
}
function labelForStatus(st){
    switch(st){
        case 0: return 'Aguardando aprovação';
        case 1: return 'Aprovado';
        case 2: return 'Recusado';
        case 3: return 'Cancelado';
        case 4: return 'Finalizado';
        case 5: return 'Em andamento';
        default: return 'Vencido';
    }
}

function fillData() {

    // Cabeçalhos (até 3 barras: página 1, página 2 e barra-just oculta)
    for (var i = 0; i <= 2; i++) {
        var ids = document.getElementsByName('idreq')[i];
        var bar = document.getElementsByName('barra_titulo')[i];
        var sts = document.getElementsByName('status_dev')[i];
        if(!ids || !bar || !sts) continue;

        ids.innerHTML += idReq;
        var st = Number(df['status'][0]);
        bar.style.backgroundColor = colorForStatus(st);
        sts.innerHTML += labelForStatus(st);
    }

    // Período
    document.getElementById('gerais').innerHTML += (df['initDate'][0] || '') + ' até ' + (df['finalDate'][0] || '');

    // Bloco gerais
    document.getElementById('solicitante').innerHTML += (df['name'][0] || '');
    document.getElementById('equipe').innerHTML += (df['sector'][0] || '');
    document.getElementById('uni_jost').innerHTML += (df['unit'][0] || '');

    // Produto / listas (já vêm formatadas pelo backend)
    document.getElementById('ct').innerHTML += (df['workCenter'][0] || '');
    document.getElementById('cod_produto').innerHTML += (df['prodCode'][0] || '');
    document.getElementById('fam_produto').innerHTML += (df['families'][0] || '');
    document.getElementById('desc_produto').innerHTML += (df['prodDescription'][0] || '');
    document.getElementById('it').innerHTML += (df['workInstruction'][0] || '');
    document.getElementById('doc_relacionado').innerHTML += (df['documents'][0] || '');
    document.getElementById('rastreabilidade').innerHTML += (df['traceability'][0] || '');
    document.getElementById('motivo').innerHTML += (df['motive'][0] || '');

    // Flags especiais (stringfy no back) -> apenas concatena nomes não vazios
    var specialList = [df['special1'][0], df['special2'][0], df['ssma'][0]].filter(function (item){ return item !== "" && item !== null && item !== undefined; });
    var specialString = 'Nenhuma';
    if (specialList.length > 1) specialString = specialList.slice(0, -1).join(', ') + ' e ' + specialList.slice(-1);
    else if (specialList.length === 1) specialString = specialList[0];

    document.getElementById('risco').innerHTML += specialString;
    document.getElementById('ana_risco').innerHTML += (df['riskAnalisys'][0] || '');
    document.getElementById('procedimentos').innerHTML += (df['procedures'][0] || '');

    // Plano de ação
    var totalItems = df_plan && df_plan['text'] ? Object.keys(df_plan['text']).length : 0;
    for (let i = 0; i < totalItems; i++) {
        document.getElementById('plano_acao').innerHTML +=
            '<div style="display: inline-block;">' +
                '<p class="lab_desc" style="width: 45vw;height: auto; white-space: pre-line;" id="acao"><b>Ação ' + (i + 1) + ': </b>' + (df_plan['text'][i] || '') + '</p><br>' +
                '<p class="lab_desc" style="width: 45vw;height: auto; white-space: pre-line;" id="responsavel"><b>Responsável  ' + (i + 1) + ': </b>' + (df_plan['name'][i] || '') + '</p><br>' +
                '<p class="lab_desc" style="width: 45vw;height: auto; white-space: pre-line;" id="data"><b> Prazo  ' + (i + 1) + ': </b>' + (df_plan['deadline'][i] || '') + '</p><br>' +
            '</div>';
    }

    // Evidências do motivo
    var imgsMot = (df['imagesMotive'][0] || '').trim();
    if (imgsMot) {
        var imagen1 = imgsMot.split('||').filter(Boolean);
        for (let k = 0; k < imagen1.length; k++) {
            var src = encodeURIComponent(imagen1[k]);
            var request = df['deviationId'][0].slice(0, -1) + '0';
            document.getElementById('imagens').innerHTML +=
                '<img class="img_left" src="/static/uploads/deviation/request/' + request + '/motive/' + src + '"/>';
        }
    }

    // Evidências dos procedimentos
    var imgsProc = (df['imagesProcedures'][0] || '').trim();
    if (imgsProc) {
        var imagen2 = imgsProc.split('||').filter(Boolean);
        for (let k = 0; k < imagen2.length; k++) {
            var src2 = encodeURIComponent(imagen2[k]);
            var request2 = df['deviationId'][0].slice(0, -1) + '0';
            document.getElementById('imagens2').innerHTML +=
                '<img class="img_left" src="/static/uploads/deviation/request/' + request2 + '/procedure/' + src2 + '"/>';
        }
    }

    // Fluxo de aprovação / Justificativas
    var reprove = 0;
    var keys = df_result && df_result['status'] ? Object.keys(df_result['status']) : [];
    for (const index of keys) {
        const status = Number(df_result['status'][index]);
        const approverSector = df_result['approverSector'][index];
        const approverName = df_result['approverName'][index] || '';
        const textDenied = df_result['textDenied'][index] || '';

        // Elementos por setor (há dois com mesmo name — um para status, outro p/ justificativa)
        const elements = document.getElementsByName(approverSector);
        const approverElement = elements && elements[0] ? elements[0] : null;
        const secondApproverElement = elements && elements[1] ? elements[1] : null;

        if (!approverElement) continue;

        if (status === 0) {
            approverElement.innerHTML = 'Aguardando Aprovação';
        } else if (status === 1) {
            approverElement.innerHTML = 'Aprovado digitalmente por ' + approverName;
        } else if (status === 2) {
            approverElement.innerHTML = 'Reprovado digitalmente por ' + approverName;

            if (reprove === 0) {
                document.getElementById('quebra-final').classList.add('quebra-pagina');
                document.getElementById('barra-just').style.display = 'block';
                reprove++;
            }
            if (secondApproverElement){
                secondApproverElement.style.display ='block';
                secondApproverElement.innerHTML +=
                    '<p class="lab_subt">Justificativa de Recusa - ' + approverSector + ': </p>' +
                    '<p class="lab_desc" style="width:95vw" readonly type="text" id="deniedText">' + textDenied + '</p>';
            }

        } else if (status === 3) { // Cancelado
            approverElement.innerHTML = 'Cancelado digitalmente por ' + approverName;

            if (reprove === 0) {
                document.getElementById('quebra-final').classList.add('quebra-pagina');
                document.getElementById('barra-just').style.display = 'block';
                if (secondApproverElement){
                    secondApproverElement.style.display ='block';
                    secondApproverElement.innerHTML +=
                        '<p class="lab_subt">Justificativa de Cancelamento - Sistemas de Qualidade: </p>' +
                        '<p class="lab_desc" style="width:95vw" readonly type="text" id="deniedText">' + textDenied + '</p>';
                }
                reprove++;
            }
        }

        // Observações Cliente/Fornecedor (apenas se não cancelado)
        if (status !== 3 && approverSector === 'Qualidade Cliente') {
            if (Number(df['notifyCostumer'][0]) === 1) {
                approverElement.innerHTML += '<p class="lab_desc" style="width:45vw;height:auto;white-space:pre-line;"><b>OBS: </b> COMUNICAR CLIENTE</p>';
            } else if (Number(df['notifyCostumer'][0]) === 0) {
                approverElement.innerHTML += '<p class="lab_desc" style="width:45vw;height:auto;white-space:pre-line;"><b>OBS: </b> NÃO COMUNICAR CLIENTE</p>';
            }
        } else if (status !== 3 && approverSector === 'Eng. Fornecedores') {
            if (Number(df['notifySupplier'][0]) === 1) {
                approverElement.innerHTML += '<p class="lab_desc" style="width:45vw;height:auto;white-space:pre-line;"><b>OBS: </b> COMUNICAR FORNECEDOR</p>';
            } else if (Number(df['notifySupplier'][0]) === 0) {
                approverElement.innerHTML += '<p class="lab_desc" style="width:45vw;height:auto;white-space:pre-line;"><b>OBS: </b> NÃO COMUNICAR FORNECEDOR</p>';
            }
        }

        // Unidade Campinas visibilidade
        if ((df['unit'][0] || '') === 'Caxias do Sul') {
            var u = document.getElementById("unitCampinas");
            if (u) u.innerHTML = 'Não aplicavel';
        }
    }
}

/* === ADIÇÃO: Botão X igual ao da imagem (lado direito, grande, vermelho) === */
(function addRightSideX() {
    try {
        // Evita inserir duas vezes
        if (document.getElementById('select_back')) return;

        // 1) Injeta CSS aditivo
        const css = document.createElement('style');
        css.textContent = `
            #select_back {
                position: fixed;
                top: 1.5vh;
                right: 2vw;                 /* <-- lado DIREITO */
                z-index: 9999;
                font-size: 72px;            /* GRANDE como na referência */
                font-weight: 900;
                line-height: 0.8;
                text-decoration: none;
                cursor: pointer;
                color: #C5224C;             /* TOM VERMELHO como na imagem */
                background: transparent;    /* sem bolha */
                border: none;
                transition: transform 0.15s ease, opacity 0.15s ease;
                user-select: none;
            }
            #select_back:hover {
                transform: scale(1.08);
                opacity: .9;
            }
            #select_back:active {
                transform: scale(0.95);
            }
            @media print {
                #select_back { display: none; }
            }
        `;
        document.head.appendChild(css);

        // 2) Cria o elemento
        const x = document.createElement('a');
        x.id = 'select_back';
        x.innerHTML = '&times;'; // X puro
        x.href = '/desvios/consultar'; // fallback

        // 3) Comportamento: se houver histórico, volta; senão vai pro href
        x.addEventListener('click', function (e) {
            if (window.history.length > 1 && document.referrer) {
                e.preventDefault();
                window.history.back();
            }
        });

        // 4) Injeta no body
        document.body.appendChild(x);

    } catch (err) {
        console.warn("Erro ao adicionar X de voltar:", err);
    }
})();

fillData();
