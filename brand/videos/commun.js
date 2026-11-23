/* Lecteur commun des videos verticales (1080 x 1920, 9:16).
   Parametres d'adresse :
     ?t=4.5        fige la scene a 4,5 s (images fixes, couvertures, export image par image)
     ?capture      scene a l'echelle 1, sans barre de commande (rendu par Chrome sans interface)
     ?enregistrer  scene de 540 x 960 points (1080 x 1920 pixels sur un ecran Retina), fond noir,
                   la lecture attend la barre d'espace pour laisser lancer l'enregistrement d'ecran
     ?mouvement    joue l'animation meme si le systeme demande moins de mouvement */
(function () {
  "use strict";
  var q = new URLSearchParams(location.search);
  var racine = document.documentElement;
  var scene = document.querySelector(".scene");
  var cadre = document.querySelector(".cadre");
  var duree = parseFloat(scene.dataset.duree);
  var reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches && !q.has("mouvement");

  // Texte tape lettre par lettre : <span data-taper="debut,ecart">texte</span>
  document.querySelectorAll("[data-taper]").forEach(function (el) {
    var p = el.dataset.taper.split(",");
    var debut = parseFloat(p[0]);
    var ecart = parseFloat(p[1]);
    var texte = el.textContent;
    el.textContent = "";
    el.setAttribute("aria-label", texte);
    Array.from(texte).forEach(function (c, i) {
      var s = document.createElement("span");
      s.className = "car";
      s.setAttribute("aria-hidden", "true");
      s.textContent = c;
      s.style.animationDelay = (debut + i * ecart).toFixed(3) + "s";
      el.appendChild(s);
    });
  });

  function animations() {
    return document.getAnimations().filter(function (a) {
      return !a.effect || !a.effect.target || scene.contains(a.effect.target);
    });
  }

  function figer(sec) {
    animations().forEach(function (a) {
      a.pause();
      a.currentTime = sec * 1000;
    });
  }

  function jouer() {
    animations().forEach(function (a) {
      a.currentTime = 0;
      a.play();
    });
    depart = performance.now();
  }

  function ajuster() {
    if (q.has("capture")) {
      racine.classList.add("capture");
      return;
    }
    var k;
    if (q.has("enregistrer")) {
      racine.classList.add("enregistrer");
      k = 0.5;
    } else {
      var barre = document.querySelector(".commandes");
      var h = barre ? barre.offsetHeight + 24 : 0;
      k = Math.min((window.innerWidth - 32) / 1080, (window.innerHeight - h - 32) / 1920);
    }
    scene.style.transform = "scale(" + k + ")";
    cadre.style.width = 1080 * k + "px";
    cadre.style.height = 1920 * k + "px";
  }

  var depart = performance.now();
  ajuster();
  window.addEventListener("resize", ajuster);

  var t = q.get("t");
  if (t !== null) {
    figer(parseFloat(t));
  } else if (reduit) {
    figer(duree);
    var avis = document.querySelector(".avis-mouvement");
    if (avis) avis.hidden = false;
  } else if (q.has("enregistrer")) {
    figer(0);
    document.addEventListener("keydown", function (e) {
      if (e.code === "Space") {
        e.preventDefault();
        jouer();
      }
    });
  }

  var bouton = document.querySelector("[data-rejouer]");
  if (bouton) bouton.addEventListener("click", jouer);
  var horloge = document.querySelector("[data-horloge]");
  if (horloge && t === null && !reduit) {
    (function tic() {
      var s = Math.min((performance.now() - depart) / 1000, duree);
      horloge.textContent = s.toFixed(1).replace(".", ",") + " s / " + String(duree).replace(".", ",") + " s";
      requestAnimationFrame(tic);
    })();
  }
})();
