function formatMoney(input) {
    // Remove caracteres não numéricos
    let valor = input.value.replace(/\D/g, '');

    // Adiciona a formatação de dinheiro
    if (valor.length > 2) {
        valor = 'R$ ' + (parseInt(valor) / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } else if (valor.length === 2) {
        valor = 'R$ 0,' + valor;
    } else if (valor.length === 1) {
        valor = 'R$ 0,0' + valor;
    } else if (valor === '') {
        valor = 'R$ 0,00';
    } else {
        valor = 'R$ ' + (parseInt(valor) / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Define o valor formatado de volta no campo de entrada
    input.value = valor;
}

coord = {{coord}}
for (dados in coord) {
    document.getElementById('coordenador').innerHTML += '<option value=' + coord[dados][1] + '>' + coord[dados][0] + '</option>'
}