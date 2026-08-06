let currentSlide = 0;
const containers = document.querySelectorAll('.container');
const totalSlides = containers.length;

function showSlide(index) {
    containers.forEach((container, i) => {
        container.classList.toggle('active', i === index);
    });

    document.getElementById('prevBtn').disabled = index === 0;
    document.getElementById('nextBtn').disabled = index === totalSlides - 1;

    showData()
}

function nextSlide() {
    if (currentSlide < totalSlides - 1 && gettingData == false) {
        currentSlide++;
        showSlide(currentSlide);
    }
}

function prevSlide() {
    if (currentSlide > 0 && gettingData == false) {
        currentSlide--;
        showSlide(currentSlide);
    }
}

function showData() {
    window[`chart${currentSlide}`]()
}

document.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowRight') {
        // Seta direita: vai para o próximo slide
        nextSlide();
    } else if (event.key === 'ArrowLeft') {
        // Seta esquerda: volta para o slide anterior
        prevSlide();
    }
});

function openStops(presentationArea) {

    const year = document.getElementById('yearInput').value;
    const week = document.getElementById('weekInput').value;

    window.open(`/oee/paradas?preload=${motiveId}&year=${year}&week=${week}&area=${presentationArea}`)
}

function openMaintenance() {

    const year = document.getElementById('yearInput').value;
    const week = document.getElementById('weekInput').value;

    window.open(`/manutencao/disponibilidade?preload=5&year=${year}&week=${week}`)
}