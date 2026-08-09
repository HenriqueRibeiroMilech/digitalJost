function init() {
    var reqId = {{reqId | tojson}};
    var cmd = {{cmd | tojson}};
    var requestType = {{requestType | tojson}}
    if (requestType == 'melhorias') {
        if (cmd == 'decline') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:17vh;">
                    <p class="title">Justifique a não aprovação!</p><br>
                    <p class="desc">Descreva o motivo de não aprovar a demanda do solicitante</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=decline&id=` + reqId + `" method="post">
                        <textarea id="textarea" name="justificativa" required class="edit_filter"></textarea>
                        <br><br>
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw)" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Recusar</button>
                    </form>
                </div>`

        } else if (cmd == 'start') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:20vh;">
                    <p class="title">Defina um prazo para a entrega!</p><br>
                    <p class="desc">Informe a data de finalização da demanda ao solicitante</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=start&id=` + reqId + `" method="post">
                        <input style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1vw);height:calc(3vh + 4vw);width:50vw;" type="date" name="prazoEntrega" required class="edit_filter">
                        <br><br>
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw);" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Iniciar</button>
                    </form>
                </div>`

        } else if (cmd == 'pause') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:0;">
                    <p class="title">Justifique a pausa no desenvolvimento!</p><br>
                    <p class="desc">Informe o solicitante das razões da interrupção da demanda</p>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=pause&id=` + reqId + `" method="post">
                        <textarea id="textarea" name="justificativa" required class="edit_filter" placeholder="Escreva aqui..."></textarea>
                        <br><br>
                        <p class="desc">Defina um prazo <b><i>MÁXIMO</i></b> para retomar o desenvolvimento</p>
                        <input style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1vw);height:calc(3vh + 4vw);width:50vw;" type="date" name="dataUnpause" required class="edit_filter">
                        <br><br>
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw);" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Pausar</button>
                        <br><br>
                    </form>
                </div>`

        } else if (cmd == 'unpause' || cmd == 'reprogram') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:20vh;">
                    <p class="title">Defina um novo prazo para a entrega!</p><br>
                    <p class="desc">Informe a data de finalização da demanda ao solicitante</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=` + cmd + `&id=` + reqId + `" method="post">
                        <input style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1vw);height:calc(3vh + 4vw);width:50vw;" type="date" name="prazoEntrega" required class="edit_filter">
                        <br><br>
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw);" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Reprogramar</button>
                    </form>
                </div>`

        } else if (cmd == 'finish') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:20vh;">
                    <p class="title">Obrigado por finalizar a entrega!</p><br>
                    <p class="desc">Finalize o processo e notifique o solicitante clicando no botão abaixo</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=finish&id=` + reqId + `" method="post">
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw);" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Finalizar</button>
                    </form>
                </div>`
        }
    } else {
        if (cmd == 'approveBoss') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:20vh;">
                    <p class="title">Aprovar solicitação!</p><br>
                    <p class="desc">Após a aprovação, a solicitação sera enviada para a área desenvolvedora avaliar o projeto.</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=approveBoss&id=` + reqId + `" method="post">
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw);" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Aprovar desenvolvimento</button>
                    </form>
                </div>`
        } else if (cmd == 'deniedBoss') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:17vh;">
                    <p class="title">Justifique a não aprovação!</p><br>
                    <p class="desc">Descreva o motivo de não aprovar a solicitação de projeto do solicitante</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=deniedBoss&id=` + reqId + `" method="post">
                        <textarea id="textarea" name="just" required class="edit_filter"></textarea>
                        <br><br>
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw)" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Recusar</button>
                    </form>
                </div>`

        } else if (cmd == 'approveArea') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:20vh;">
                    <p class="title">Aprovar desenvolvimento!</p><br>
                    <p class="desc">Após aprovar, você deve entrar em contato com o solicitante, em até uma semana, para alinhar espectativas.</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=approveArea&id=` + reqId + `" method="post">
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw);" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Aprovar desenvolvimento</button>
                    </form>
                </div>`
        } else if (cmd == 'deniedArea') {
            document.querySelector('.page_body').innerHTML += `
                <div class="message_container" style="margin-top:17vh;">
                    <p class="title">Justifique a não aprovação!</p><br>
                    <p class="desc">Descreva o motivo de não aprovar a solicitação de projeto do solicitante</p><br>
                    <form action="/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=deniedArea&id=` + reqId + `" method="post">
                        <textarea id="textarea" name="just" required class="edit_filter"></textarea>
                        <br><br>
                        <button style="padding:calc(0.8vh + 0.8vw);font-size:calc(1vh + 1.4vw);height:calc(3vh + 4vw);width:calc(15vh + 30vw)" id="edit_ask" type="submit" style="font-size: calc(1vh + 2vw)">Recusar</button>
                    </form>
                </div>`
        }

    }

}

init();

function animate() {
    document.querySelector(".page_body").style.opacity= "1";
    document.querySelector(".page_body").style.marginTop= "0vh";
}
