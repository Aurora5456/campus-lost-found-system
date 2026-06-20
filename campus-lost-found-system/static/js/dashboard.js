(function () {
  const dataEl = document.getElementById("dashboard-data");
  if (!dataEl || typeof Chart === "undefined") {
    return;
  }
  const data = JSON.parse(dataEl.textContent);
  const green = "#117c70";
  const amber = "#f4b24d";

  new Chart(document.getElementById("trendChart"), {
    type: "line",
    data: {
      labels: data.trendLabels,
      datasets: [
        {
          label: "新增帖子",
          data: data.trendCounts,
          borderColor: green,
          backgroundColor: "rgba(17, 124, 112, 0.15)",
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  new Chart(document.getElementById("typeChart"), {
    type: "doughnut",
    data: {
      labels: ["失物", "招领"],
      datasets: [
        {
          data: data.typeCounts,
          backgroundColor: [green, amber],
        },
      ],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });

  new Chart(document.getElementById("categoryChart"), {
    type: "bar",
    data: {
      labels: data.categoryLabels,
      datasets: [
        {
          label: "帖子数",
          data: data.categoryCounts,
          backgroundColor: green,
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
})();
