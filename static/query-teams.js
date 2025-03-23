document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("query-form").addEventListener("submit", function(event) {
        event.preventDefault();

        const formData = new FormData(this);
        const queryParams = new URLSearchParams(formData).toString();

        fetch('/query-teams', {
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

            if (!data.teams || data.teams.length === 0) {
                resultsList.innerHTML = "<li>No results found</li>";
                return;
            }

            data.teams.forEach(team => {
                const listItem = document.createElement('li');
                listItem.textContent = `Team: ${team.Name}, Year_Founded: ${team.Year_Founded}, Titles: ${team.Total_Constructor_Titles}`;
                resultsList.appendChild(listItem);
            });
        })
        .catch(error => console.error('Error:', error));
    });
});

            


