(function () {
    'use strict';

    const form = document.getElementById('uploadForm');
    if (!form) {
        return;
    }

    form.addEventListener('reset', function () {
        form.classList.remove('was-validated');
    });

    form.addEventListener('submit', function (event) {
        form.classList.add('was-validated');

        const fileInput1 = document.getElementById('fileInput1');
        const fileInput2 = document.getElementById('fileInput2');
        let isValid = form.checkValidity();

        if (!fileInput1.files.length) {
            fileInput1.classList.add('is-invalid');
            isValid = false;
        } else {
            fileInput1.classList.remove('is-invalid');
        }

        if (!fileInput2.files.length) {
            fileInput2.classList.add('is-invalid');
            isValid = false;
        } else {
            fileInput2.classList.remove('is-invalid');
        }

        if (!isValid) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
    }, false);
}());
