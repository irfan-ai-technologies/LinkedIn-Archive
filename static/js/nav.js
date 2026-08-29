(function () {
  "use strict";

  document.addEventListener("keydown", function (event) {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    var target = event.target;
    var tag = target && target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || (target && target.isContentEditable)) return;

    var searchInput = document.getElementById("search-input");
    if (searchInput) {
      event.preventDefault();
      searchInput.focus();
      return;
    }
    var searchLink = document.querySelector(".search-link");
    if (searchLink) {
      event.preventDefault();
      window.location.href = searchLink.getAttribute("href");
    }
  });
})();
