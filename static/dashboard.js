(async function(){
  try{
    const res = await fetch('/api/summary');
    const data = await res.json();
    const ctx = document.getElementById('barChart');
    if(!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.months,
        datasets: [
          { label: 'Card Rentals', data: data.rentals },
          { label: 'Salaries', data: data.salaries },
          { label: 'Expenses', data: data.expenses }
        ]
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true } }
      }
    });
  }catch(e){
    console.error(e);
  }
})();
