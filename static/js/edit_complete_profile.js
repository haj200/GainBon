const fields = ['nom', 'prenom', 'ville', 'telephone', 'adresse', 'profession', 'sexe'];

function goToStep2() {
  console.log("→ goToStep2 appelé");
  for (let field of fields) {
    const value = document.getElementById(field).value.trim();
    

    // Sauvegarder en localStorage
    localStorage.setItem('form_' + field, value);

    // Copier dans les champs cachés de l'étape 2
    const hiddenInput = document.getElementById('input_' + field);
    if (hiddenInput) hiddenInput.value = value;
  }

  localStorage.setItem('current_step', '2');
  showStep(2);
}

function showStep(step) {
  if (step === 1) {
    document.getElementById("step1").classList.remove("hidden");
    document.getElementById("step2").classList.add("hidden");
    document.getElementById("progress").style.width = "50%";
    localStorage.setItem("current_step", "1");
  } else {
    document.getElementById("step1").classList.add("hidden");
    document.getElementById("step2").classList.remove("hidden");
    document.getElementById("progress").style.width = "100%";
    localStorage.setItem("current_step", "2");
  }
}

function backToStep1() {
  showStep(1);
}

function validateForm() {
  

  
  return true;
}

function addValidationToForms(className) {
  const forms = document.querySelectorAll(`form.${className}`);
  forms.forEach(form => {
    form.addEventListener('submit', function (e) {
      if (!validateForm()) {
        e.preventDefault(); // bloque l'envoi si invalide
        alert('Formulaire invalide');
      } else {
        localStorage.clear();
        // Formulaire valide → soumission normale à form.action
        console.log(`→ Soumission du formulaire vers ${form.action}`);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  // Restaurer les champs de l'étape 1 depuis localStorage
  fields.forEach(field => {
    const value = localStorage.getItem('form_' + field);
    if (value) {
      const input = document.getElementById(field);
      if (input) input.value = value;
      const hiddenInput = document.getElementById('input_' + field);
      if (hiddenInput) hiddenInput.value = value;
    }
  });

  // Restaurer l’étape actuelle
  const currentStep = localStorage.getItem("current_step");
  showStep(currentStep === "2" ? 2 : 1);

  // Charger les options dynamiques
  fetch("/profile-data")
    .then(response => response.json())
    .then(data => {
      const naturesContainer = document.getElementById("natures");
      const citiesContainer = document.getElementById("favourite_cities");
      const categoriesContainer = document.getElementById("categories");

      // Natures
      naturesContainer.innerHTML = "";
      data.natures.forEach(nature => {
        const isChecked = window.oldPreferences?.natures?.includes(String(nature.id));
        const label = document.createElement("label");
        label.innerHTML = `<input type="checkbox" name="natures" value="${nature.id}" ${isChecked ? "checked" : ""}> ${nature.nom}`;
        naturesContainer.appendChild(label);
      });

      // Villes
      citiesContainer.innerHTML = "";
      data.cities.forEach((city, idx) => {
        const id = "city" + idx;
        const isChecked = window.oldPreferences?.cities?.includes(city);
        citiesContainer.innerHTML += `
          <input type="checkbox" id="${id}" name="favourite_cities" value="${city}" ${isChecked ? "checked" : ""}>
          <label for="${id}">${city}</label>
        `;
      });

      // Catégories
      categoriesContainer.innerHTML = "";
      data.categories.forEach(category => {
        const isChecked = window.oldPreferences?.categories?.includes(category);
        categoriesContainer.innerHTML += `
          <label><input type="checkbox" name="categories" value="${category}" ${isChecked ? "checked" : ""}> ${category}</label>
        `;
      });
    });

  // Activer la validation
  addValidationToForms('formComplete');
  addValidationToForms('formEdit');
});
