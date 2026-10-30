(function () {
  const labels = window.deviationUnitsConfig;
  const filter = document.getElementById('unit_filter');

  window.deviationUnits = {
    label(value) {
      return labels[String(value)] || 'Não informada';
    },
    selected() {
      return filter.value;
    },
    matches(value) {
      const selected = filter.value;
      const unit = String(value);
      return selected === '' || unit === selected || (selected !== '2' && unit === '2');
    }
  };

  filter.addEventListener('change', function () {
    window.filterTable();
  });
})();
