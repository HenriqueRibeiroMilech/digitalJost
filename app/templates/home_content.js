var res = {{res | tojson}}
document.getElementById("myVideo").style.transform = "translate(" + res + "%," + res + "%)";

document.getElementById("main_sidebar").style.width = "0px";
document.getElementById("app_sidebar").style.width = "0px";
document.getElementById("dem_sidebar").style.width = "0px";
document.getElementById("sol_sidebar").style.width = "0px";
document.getElementById("op_sidebar").style.width = "0px";

function animate() {
    setTimeout(function() {
        var img_div = document.getElementById('digitaljost_logo');
        img_div.style.opacity = "1";
    }, 0500)
}
