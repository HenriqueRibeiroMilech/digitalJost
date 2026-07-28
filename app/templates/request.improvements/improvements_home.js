var area = ''

function changeLoc(arg) {
   window.location = arg + area
}

function changeLoc2(arg, arg2) {
   window.location = arg + area + '&tipo=' + arg2
}

function showInfo() {
    document.querySelector(".blur_wrap").style.filter = "blur(8px)";
    document.querySelector(".blur_wrap").style.pointerEvents = "none";
    var overlay = document.querySelector(".lab_overlay");
    overlay.style.display = "block";
    overlay.style.opacity = "1";
}

function closeInfo(arg) {
    var overlay = document.querySelector(".lab_overlay");
    overlay.style.opacity = "0";
    overlay.style.display = "none";
    document.querySelector(".blur_wrap").style.filter = "none";
    document.querySelector(".blur_wrap").style.pointerEvents = "auto";

    document.getElementById('description').innerHTML += '<b> ' + arg + '!</b>'
    area = '?area=' + arg
}

showInfo()