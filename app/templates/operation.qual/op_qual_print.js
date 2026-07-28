document.title = "Informativo da Qualidade - " + {{day | tojson}}
function init() {
    var data = {{file | tojson}}

    for (let i = 0; i < data.length; i++) {
        var entry = data[i];
        var id_color = entry['Local da Ocorrencia'][0].toLowerCase();
        if (entry['Local da Ocorrencia'][0].toLowerCase() == 'cliente (não formal)') {
            var id_color = 'clientenf';
        } else if (entry['Local da Ocorrencia'][0].toLowerCase() == 'cliente (formal)') {
            var id_color = 'clientef';
        }

        if (entry['unit'][0] == '0') {
            unit = 'Caxias do Sul'
        } else {
            unit = 'Campinas'
        }

        document.getElementById('op_qual_body').innerHTML += `
            <div class="qual_event">
                <div class="qual_title_wrap" id="` + id_color + `">
                    <img class="qual_logo" src="/static/images/new_jost_logo.jpg"/>
                    <p class="qual_title">Informativo da Qualidade - ` + unit + `</p>
                    <p class="qual_desc">{{day}} || Nº ` + entry['ID'] + `</p>
                </div>

                <div class="qual_legend_wrap">
                    <div class="qual_sub_legend_wrap"><div class="color" id="interno"></div><p>Interno</p></div>
                    <div class="qual_sub_legend_wrap"><div class="color" id="clienteNF"></div><p>Cliente (Não formal)</p></div>
                    <div class="qual_sub_legend_wrap"><div class="color" id="fornecedor"></div><p>Fornecedor</p></div>
                    <div class="qual_sub_legend_wrap"><div class="color" id="clienteF"></div><p>Cliente (Formal)</p></div>
                </div>

                <div class="qual_info_wrap">
                    <div><p style="height:calc(7vw + 2.5vh);"><b>Problema: </b>` + entry['Problema'] + `</p></div>
                    <div style="float:left"><p style="width: 17vw;"><b>Reincidente: </b>` + entry['Reincidente'] + `</p></div>
                    <div style="float:left"><p style="width: 30vw;"><b>Centro de Trabalho: </b>` + entry['workCenter'] + `</p></div>
                    <div style="float:left"><p style="width: 30vw;"><b>Código do Produto: </b>` + entry['prodCode'] + `</p></div>
                </div>

                <div class="qual_legend_wrap" style="height:auto;">
                    <p class="qual_title" id="qual_fotos_title">Imagens</p>
                </div>

                <div class="qual_img_section"></div>`

        for (let k = 0; k < entry['Imagens NOK'].length; k++) {
            document.querySelectorAll('.qual_img_section')[i].innerHTML += `
                <div class="qual_img_wrap" style="background:rgb(182,21,21)">NOK  <img class="qual_img" src="/static/uploads/operation/img_nok/` + entry['ID'] + `/` + entry['Imagens NOK'][k] + `"/></div>`
        }
        for (let k = 0; k < entry['Imagens OK'].length; k++) {
            document.querySelectorAll('.qual_img_section')[i].innerHTML += `
                <div class="qual_img_wrap" style="background:#228C22">OK <img class="qual_img" src="/static/uploads/operation/img_ok/` + entry['ID'] + `/` + entry['Imagens OK'][k] + `"/></div>`
        }

        document.getElementById('op_qual_body').innerHTML += `
                <div class="qual_legend_wrap" style="height:auto;">
                    <p class="qual_title" id="qual_fotos_title">Contenção</p>
                </div>

                <div class="qual_info_wrap">
                    <div class="qual_sub_info_wrap"><p><b>O que: </b>` + entry['Contencao']['O que'] + `</p></div>
                    <div class="qual_sub_info_wrap"><p><b>Como: </b>` + entry['Contencao']['Como'] + `</p></div>
                    <div class="qual_sub_info_wrap"><p><b>Quem: </b>` + entry['Contencao']['Quem'] + `</p></div>
                </div>

                <div class="qual_info_section" id="` + id_color + `">
                    <p class="qual_cell"><b>Data Abertura: </b>{{day}}</p>
                    <p class="qual_cell"><b>Posto de Trabalho: </b>` + entry['Local da Ocorrencia'][1] + `</p>
                    <p class="qual_cell"><b>Turno de Trabalho: </b>` + entry['Turno'] + `</p>
                    <p class="qual_cell"><b>Família Produtos: </b>` + entry['Familia do Produto'] + `</p>
                </div>
            </div>
            <table>
                <tr>
                    <td colspan="3">
                        <strong>INFORMATIVO W:</strong> <input type="text" class="header-input">
                        <strong>Turno:</strong> <input type="text" class="header-input">
                        <strong>Data:</strong> <input type="text" class="date-input"> / <input type="text" class="date-input"> / <input type="text" class="date-input">
                    </td>
                </tr>
                <tr>
                    <th>Nome do Funcionário</th>
                    <th>Matrícula</th>
                    <th>Assinatura</th>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                                                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
                                                <tr>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                    <td><input type="text" class="input-field"></td>
                </tr>
            </table>
            `
    }
}

removeNav();
init();