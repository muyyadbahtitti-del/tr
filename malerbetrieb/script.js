const menu=document.querySelector('nav ul');
document.querySelector('.burger').addEventListener('click',()=>menu.classList.toggle('open'));
menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>menu.classList.remove('open')));
document.getElementById('year').textContent=new Date().getFullYear();
// Kontaktformular: öffnet das E-Mail-Programm (kein Server nötig).
// Für Versand ohne Mail-Programm später z. B. Formspree/Netlify Forms einbinden.
const MAIL='info@malerbetrieb-leipzig.de'; // TODO: eigene E-Mail eintragen
document.getElementById('form').addEventListener('submit',e=>{
  e.preventDefault();
  const d=Object.fromEntries(new FormData(e.target));
  const body=`Name: ${d.name}\nTelefon: ${d.tel}\nE-Mail: ${d.mail}\nObjekt: ${d.art}\n\n${d.msg}`;
  location.href=`mailto:${MAIL}?subject=${encodeURIComponent('Anfrage: '+d.art)}&body=${encodeURIComponent(body)}`;
  document.getElementById('note').textContent='Vielen Dank! Ihr E-Mail-Programm öffnet sich – bitte absenden.';
});
