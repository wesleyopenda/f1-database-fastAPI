document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("query-form").addEventListener("submit", function(event) {
        event.preventDefault();

        const formData = new FormData(this);

        fetch('/query-drivers', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            const resultsList = document.getElementById('results');
            resultsList.innerHTML = "";

            if (data.drivers.length === 0) {
                resultsList.innerHTML = "<li>No results found</li>";
                return;
            }

            data.drivers.forEach(driver => {
                const listItem = document.createElement('li');
                listItem.textContent = JSON.stringify(driver);
                resultsList.appendChild(listItem);
            });
        })
        .catch(error => console.error('Error:', error));
    });
});
