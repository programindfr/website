async function screenSize() {
    let width = screen.width;
    document.getElementById("width").innerHTML = "Largeur de l'écran : " + width + " pixels";

    let height = screen.height;
    document.getElementById("height").innerHTML = "Hauteur de l'écran : " + height + " pixels";
}

async function addFile(data, elementId, textId) {
    document.getElementById(textId).innerHTML = "Chargement en cours ...";
    rotate(elementId, 6, 4);
    data.form.submit();
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function rotate(elementId, timeSleep, angle) {
    let rotateTurn = 0;
    let element = document.getElementById(elementId);
    element.style.opacity = 1;
    while (true) {
        rotateTurn += angle;
        element.style.transform = "rotate(" + rotateTurn + "deg)";
        await sleep(timeSleep);
    }
}

function makeColor(red, green, blue, r, g, b) {
    const rgb = [red + r, green + g, blue + b];
    for (let i=0; i<3; i++) {
        if (rgb[i] > 255) {
            rgb[i] -= 255;
        } else if (rgb[i] < 0) {
            rgb[i] += 255;
        }
        const hex = rgb[i].toString(16);
        rgb[i] = hex.length === 1 ? '0' + hex : hex;
    }
    return '#' + rgb.join('');
}

async function color(colorValue) {
    if (colorValue !== '') {
        document.querySelector(":root").style.setProperty("--color-1", colorValue);
        const red = parseInt(colorValue.substring(1, 3), 16);
        const green = parseInt(colorValue.substring(3, 5), 16);
        const blue = parseInt(colorValue.substring(5, 7), 16);
        document.querySelector(":root").style.setProperty("--color-2", makeColor(red, green, blue, 50, 85, 50));
        document.querySelector(":root").style.setProperty("--color-3", makeColor(red, green, blue, 0, -128, 255));
    }
}

async function timeout(textDisplay, textId, s) {
    for (let i=s; i>=0; i--) {
        let hours = (i-i%3600)/3600;
        let minutes = ((i-hours*3600)-((i-hours*3600)%60))/60;
        let seconds = i-hours*3600-minutes*60;
        document.getElementById(textId).innerHTML = textDisplay + ": " + hours + "h " + minutes + "m " + seconds +"s";
        await sleep(1000);
    }
}