'use strict';

app.controller('profileController', function($scope, $http, $state, $uibModal, $cookieStore, webchatService) {
  
  $scope.$state = $state;
  
  var loginObject = $cookieStore.get("login");
  if (angular.isUndefined(loginObject)) {
    console.log("User is not logged in.");
    $state.go('home');
    return;
  }
  
  $scope.emailAddress = loginObject["user"]["email-address"];
  $scope.apiKey = loginObject["user"]["api-key"];
  
  $scope.gravatarHash = CryptoJS.MD5($scope.emailAddress.toLowerCase()).toString();
  
  
  
  $scope.resetApiKeyButtonClicked = function() {
    
    if ($scope.apiKeyResetInProgress) {
      return false;
    }
    
    $scope.apiKeyChangeSuccessful = false;
    $scope.apiKeyResetInProgress = true;
    
    webchatService.resetApiKey()
      .then(function(newApiKey) {
        $scope.showApiKey = false;
        $scope.apiKeyChangeSuccessful = true;
        $scope.apiKeyResetInProgress = false;
        $scope.apiKey = newApiKey;
      })
      .catch(function(errorReason) {
        $scope.apiKeyResetInProgress = false;
        if (errorReason !== "Other") {
          alert(errorReason);
        }
        else {
          alert("An unexpected error occurred.");
        }
      })
  }
  
});