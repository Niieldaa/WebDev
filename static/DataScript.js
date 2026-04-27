function submitTime() {
    const data = {
        season: document.getElementById("seasonInput").value,
        race: document.getElementById("raceInput").value,
        name: document.getElementById("userName").value,
        team: document.getElementById("userTeam").value,
        time: document.getElementById("userTime").value
    };

    fetch('/add_entry', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(() => {
        loadResults();
        alert("Added!");
        // Clear inputs after submission
        document.getElementById("userName").value = "";
        document.getElementById("userTeam").value = "";
        document.getElementById("userTime").value = "";
    });
}

function deleteEntry(id) {
    if(confirm("Are you sure you want to delete this entry?")) {
        fetch('/delete_entry', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id})
        }).then(() => loadResults());
    }
}

function loadResults() {
    const season = document.getElementById("seasonInput").value;
    const race = document.getElementById("raceInput").value;
    const finishBody = document.querySelector("#finishTable tbody");
    const fastestBody = document.querySelector("#fastestTable tbody");

    finishBody.innerHTML = "<tr><td colspan='4'>Loading...</td></tr>";
    fastestBody.innerHTML = "<tr><td colspan='6'>Loading...</td></tr>";

    fetch(`/results?season=${season}&race=${race}`)
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                finishBody.innerHTML = "<tr><td colspan='4'>Data not found.</td></tr>";
                fastestBody.innerHTML = "<tr><td colspan='6'>Data not found.</td></tr>";
                return;
            }

            // the setup
            finishBody.innerHTML = "";
            data.finish_order.forEach(d => {
                const isUser = d.isUser;
                const row = `
                    <tr class="${isUser ? 'user-row' : ''}">
                        <td>${d.Position}</td>
                        <td>${d.Abbreviation}</td>
                        <td>${d.TeamName}</td>
                        <td>${d.Time}</td>
                        <td style="font-weight: bold;">${d.Gap}</td>
                    </tr>`;
                finishBody.insertAdjacentHTML('beforeend', row);
            });

            // Render Fastest Laps
            fastestBody.innerHTML = "";
            data.fastest_laps.forEach(d => {
                const isUser = d.id !== null;
                const row = `
                    <tr class="${isUser ? 'user-row' : ''}">
                        <td>${d.Position}</td>
                        <td>${d.Abbreviation}</td>
                        <td>${d.TeamName}</td>
                        <td>${d.LapTime}</td>
                        <td>${d.Gap}</td>
                        <td>${isUser ? `<button class="del-btn" onclick="deleteEntry(${d.id})">Delete</button>` : ''}</td>
                    </tr>`;
                fastestBody.insertAdjacentHTML('beforeend', row);
            });
        })
        .catch(err => {
            console.error("Error fetching results:", err);
            finishBody.innerHTML = "<tr><td colspan='4'>Error connecting to server.</td></tr>";
        });
}

// Load results on initial page load - we like
document.addEventListener('DOMContentLoaded', loadResults);