chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension Installed');
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'medicine-reminder') {
    showNotification(message.name);
  }
});

function showNotification(medicineName) {
  chrome.notifications.create('', {
    type: 'basic',
    iconUrl: 'images/icon.jpg',
    title: 'Medicine Reminder',
    message: `It's time to take your ${medicineName}!`,
    priority: 2
  }, function(notificationId) {
    if (chrome.runtime.lastError) {
      console.error(chrome.runtime.lastError.message);
    } else {
      console.log('Notification shown with ID:', notificationId);
    }
  });
}
