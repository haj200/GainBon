
  // 1. Récupération des éléments
  const signUpButton = document.getElementById('signUp');
  const signInButton = document.getElementById('signIn');
  const container = document.getElementById('container');

  // 2. Lecture du type de formulaire à afficher (envoyé par Flask)
  const formType = "{{ form_type }}";  // 'sign-in' ou 'sign-up'

  // 3. Appliquer la classe au chargement de la page
  if (formType === 'sign-up') {
    container.classList.add("right-panel-active");
  } else {
    container.classList.remove("right-panel-active");
  }

  // 4. Réactiver les boutons
  signUpButton.addEventListener('click', () => {
    container.classList.add("right-panel-active");
  });

  signInButton.addEventListener('click', () => {
    container.classList.remove("right-panel-active");
  });

