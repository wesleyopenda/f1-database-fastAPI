document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("query-form").addEventListener("submit", function(event) {
        event.preventDefault();

        const formData = new FormData(this);
        const queryParams = new URLSearchParams(formData).toString();

        fetch('/query-drivers', {
            method: 'POST',
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: queryParams
        })
        .then(response => response.json())
        .then(data => {
            const resultsList = document.getElementById('results');
            resultsList.innerHTML = "";

            if (!data.drivers || data.drivers.length === 0) {
                resultsList.innerHTML = "<li>No results found</li>";
                return;
            }

            data.drivers.forEach(driver => {
                const listItem = document.createElement('li');
                listItem.textContent = `Name: ${driver.Name}, Age: ${driver.Age}, Wins: ${driver.total_race_wins}`;
                resultsList.appendChild(listItem);
            });
        })
        .catch(error => console.error('Error:', error));
    });
});
