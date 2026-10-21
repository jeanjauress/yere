// Favoris en AJAX (le formulaire fonctionne aussi sans JavaScript).
document.addEventListener("submit", async (e) => {
  const form = e.target;
  if (!form.matches("form.js-fav")) return;
  e.preventDefault();
  try {
    const res = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (res.redirected || !res.ok) { window.location = res.url; return; }
    const data = await res.json();
    const icon = form.querySelector("i");
    icon.className = data.favorite ? "bi bi-heart-fill text-danger" : "bi bi-heart";
    const count = form.querySelector(".fav-count");
    if (count) count.textContent = data.count;
  } catch (_) { form.submit(); }
});

// Galerie de la fiche article.
document.querySelectorAll(".gallery-thumb").forEach((t) => {
  t.addEventListener("click", () => {
    document.getElementById("gallery-main").src = t.dataset.full;
    document.querySelectorAll(".gallery-thumb").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
  });
});

// Messagerie : se placer sur le dernier message.
const chat = document.querySelector(".chat-box");
if (chat) chat.scrollTop = chat.scrollHeight;
