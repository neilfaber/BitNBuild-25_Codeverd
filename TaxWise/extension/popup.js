document.addEventListener('DOMContentLoaded', function() {
  const appointments = [
    { date: '2024-09-28', time: '10:30 PM', doctor: 'Haldi', location: 'Dahisar' },
    { date: '2024-09-31', time: '02:00 PM', doctor: 'Sangeet', location: 'Borivali' }
  ];

  const medicines = [
    { name: 'Contact planner', time: '08:38 PM' },
    { name: 'Decoration final', time: '02:33 PM' },
    { name: 'Payments clearance', time: '09:45 PM' }
  ];

  function parseDateTime(date, time) {
    const [year, month, day] = date.split('-').map(Number);
    let [hour, minute] = time.split(' ')[0].split(':').map(Number);
    const period = time.split(' ')[1];

    if (period === 'PM' && hour !== 12) {
      hour += 12;
    } else if (period === 'AM' && hour === 12) {
      hour = 0;
    }

    return new Date(year, month - 1, day, hour, minute);
  }

  function updateUI() {
    const now = new Date();
    console.log(`Current time: ${now.toLocaleString()}`);

    const nextAppointment = appointments.find(app => {
      return parseDateTime(app.date, app.time) > now;
    });

    const nextAppointmentElement = document.getElementById('next-appointment');
    const countdownElement = document.getElementById('appointment-countdown');

    if (nextAppointment) {
      const appointmentDate = parseDateTime(nextAppointment.date, nextAppointment.time);
      nextAppointmentElement.textContent = `${nextAppointment.date} - ${nextAppointment.time}  ${nextAppointment.doctor} at ${nextAppointment.location}`;

      function updateCountdown() {
        const now = new Date();
        const diff = appointmentDate - now;
        if (diff <= 0) {
          countdownElement.textContent = 'Time’s up!';
          clearInterval(countdownInterval);
          return;
        }
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);
        countdownElement.textContent = `Time left: ${days}d ${hours}h ${minutes}m ${seconds}s`;
      }

      updateCountdown();
      const countdownInterval = setInterval(updateCountdown, 1000);
    } else {
      nextAppointmentElement.textContent = 'No upcoming appointments.';
      countdownElement.textContent = '';
    }

    const appointmentsList = document.getElementById('appointments-list');
    appointmentsList.innerHTML = '';
    appointments.forEach(app => {
      const div = document.createElement('div');
      div.className = 'item';
      div.innerHTML = `<span>${app.date} - ${app.time} with ${app.doctor} at ${app.location}</span><span class="timestamp">${app.date} ${app.time}</span>`;
      appointmentsList.appendChild(div);
    });

    const medicinesList = document.getElementById('medicines-list');
    medicinesList.innerHTML = '';
    medicines.forEach(med => {
      const div = document.createElement('div');
      div.className = 'item';
      div.innerHTML = `<span>${med.name} at ${med.time}</span><span class="timestamp">${med.time}</span>`;
      medicinesList.appendChild(div);

      scheduleNotification(med);
    });
  }

  function scheduleNotification(medicine) {
    const now = new Date();
    let [hour, minute] = medicine.time.split(':').map(Number);
    let period = 'AM';

    if (medicine.time.includes('PM')) {
      period = 'PM';
    }

    let hours24 = hour;
    if (period === 'PM' && hours24 !== 12) {
      hours24 += 12;
    } else if (period === 'AM' && hours24 === 12) {
      hours24 = 0;
    }

    const medicineTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hours24, minute);
    console.log(`Medicine time for ${medicine.name}: ${medicineTime.toLocaleString()}`);
    console.log(`Current time: ${now.toLocaleString()}`);

    if (medicineTime > now) {
      const timeUntilNotification = medicineTime - now;
      console.log(`Time until notification for ${medicine.name}: ${timeUntilNotification / 1000} seconds.`);

      setTimeout(() => {
        try {
          chrome.runtime.sendMessage({ type: 'medicine-reminder', name: medicine.name });
        } catch (e) {
          console.error('Error sending message to background script:', e);
        }
      }, timeUntilNotification);
    } else {
      console.log(`Medicine time for ${medicine.name} has already passed for today.`);
    }
  }

  updateUI();

  document.getElementById('emergencyButton').addEventListener('click', () => {
    const email = 'yyash7379@gmail.com';
    const subject = encodeURIComponent('Emergency Contact');
    const body = encodeURIComponent('Dear Doctor,\n\nI am writing to inform you of an emergency situation. Please respond as soon as possible.\n\nBest regards,\n[Your Name]');
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${email}&su=${subject}&body=${body}`;
    window.open(gmailUrl, '_blank');
  });
});
