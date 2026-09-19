(function(){
  var fontLink = document.createElement('link');
  fontLink.rel = 'stylesheet';
  fontLink.href = 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Public+Sans:wght@400;500;600;700&display=swap';
  fontLink.media = 'print';
  fontLink.onload = function(){ this.media = 'all'; };
  document.head.appendChild(fontLink);
})();
