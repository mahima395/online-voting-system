// Small helpers for the Online Voting System.
// The server performs all the real checks; this file only improves usability.
document.addEventListener("DOMContentLoaded", function () {
    // Ask before submitting any form that has a data-confirm message (for example delete).
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    // Ask for confirmation with the candidate name before a vote is submitted.
    var voteForm = document.getElementById("vote-form");
    if (voteForm) {
        voteForm.addEventListener("submit", function (event) {
            var selected = voteForm.querySelector("input[name='candidate_id']:checked");
            if (!selected) {
                event.preventDefault();
                window.alert("Please select a candidate.");
                return;
            }
            var message = "You are voting for " + selected.dataset.name +
                ". You cannot change your vote later. Continue?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    }

    // Check that both password fields match on the registration form.
    var registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", function (event) {
            var password = registerForm.querySelector("input[name='password']").value;
            var confirmPassword = registerForm.querySelector("input[name='confirm_password']").value;
            if (password !== confirmPassword) {
                event.preventDefault();
                window.alert("Password and confirm password do not match.");
            }
        });
    }
});
