(function () {
    'use strict';
    const printButton = document.querySelector('[data-print-document]');
    if (printButton) {
        printButton.addEventListener('click', async function () {
            const label = printButton.textContent;
            printButton.disabled = true;
            printButton.textContent = 'Preparando impressão...';
            printButton.setAttribute('aria-busy', 'true');
            try {
                const images = Array.from(document.querySelectorAll('.qsb-record-photo img'));
                images.forEach(function (image) { image.loading = 'eager'; });
                if (document.fonts) { await document.fonts.ready; }
                await Promise.all(images.map(function (image) {
                    if (image.complete) { return Promise.resolve(); }
                    return new Promise(function (resolve) {
                        image.addEventListener('load', resolve, { once: true });
                        image.addEventListener('error', resolve, { once: true });
                    });
                }));
                window.print();
            } finally { printButton.disabled = false; printButton.textContent = label; printButton.removeAttribute('aria-busy'); }
        });
    }
    function showImageError(image) {
        image.hidden = true;
        image.parentElement.querySelector('.qsb-photo-unavailable').hidden = false;
    }
    document.querySelectorAll('.qsb-record-photo img').forEach(function (image) {
        image.addEventListener('error', function () { showImageError(image); });
        if (image.complete && !image.naturalWidth) { showImageError(image); }
    });
}());
