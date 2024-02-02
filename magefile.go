//go:build mage

package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"os"
	"os/user"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/joho/godotenv"
	"github.com/magefile/mage/sh"
)

const REQUST_COUNT int = 10

// login to aws sso
func Login() error {
	loadEnvironments()
	return sh.RunV("aws", "sso", "login")
}

func Bootstrap() error {
	fmt.Println("Bootstraping...")
	sh.RunV("python3", "-m", "venv", ".venv")
	sh.RunV(".venv/bin/pip", "install", "-r", "requirements.txt")
	sh.RunV(".venv/bin/pip", "install", "-r", "requirements-dev.txt")
	return sh.RunV("cdk", "synth")
}

// deploy this stack to your default AWS
func Test() error {
	return sh.RunV("pytest", "-v")
}

// Send concurent api request to the given endpoint
func ApiTest() {
	SendApiRequests()
}

// deploy dev  stack to your default AWS
func DeployDev() {
	loadEnvironments()
	setDevStage()
	sh.RunV("cdk", "deploy", "--app", "python3 dev-app.py", "--require-approval=never")
	usetDevStage()
}

// deploy dev  stack to your default AWS
func BootstrapDev() {
	loadEnvironments()
	setDevStage()
	sh.RunV("cdk", "bootstrap", "--app", "python3 dev-app.py", "--require-approval=never")
	usetDevStage()
}

// deploy dev  stack to your default AWS
func DeployProd() {
	loadEnvironments()
	setProdStage()
	sh.RunV("cdk", "deploy", "--app", "python3 prod-app.py", "--require-approval=never")
	usetDevStage()
}

// destroy dev  stack to your default AWS
func DestroyDev() {
	loadEnvironments()
	setDevStage()
	sh.RunV("cdk", "destroy", "--app", "python3 dev-app.py", "--require-approval=never")
	usetDevStage()
}

// list all stacks in the app
func Ls() error {
	return sh.RunV("cdk", "ls")
}

// synth cdk (Do this only once)
func Synth() {
	loadEnvironments()
	setDevStage()
	// sh.RunV("cdk", "synth")
	sh.RunV("cdk", "synth")
	usetDevStage()
}

// compare deployed stack with current state
func Diff() error {
	return sh.RunV("cdk", "diff")
}

// Check for ipv6
func CheckIp(hostname string) error {
	fmt.Println("Checking", hostname)
	if !isIPv6Ready(hostname) {
		return errors.New("IPv6 not ready")
	}
	return nil
}

// format source code
func Format() error {
	if err := formatSourceCode("infra"); err != nil {
		return err
	}
	if err := formatSourceCode("services"); err != nil {
		return err
	}
	if err := formatSourceCode("tests"); err != nil {
		return err
	}
	if err := formatSourceCode("tools"); err != nil {
		return err
	}
	return nil
}

// Lint source code
func Lint() error {
	sh.RunV("pylint", "infra", "layers", "services", "--fail-under=6.5")
	sh.RunV("black", "--check", "services", "infra", "tests")
	return nil
}

// private functions

func isIPv6Ready(hostname string) bool {
	addrs, err := net.LookupIP(hostname)
	if err != nil {
		fmt.Println(err)
		return false
	}

	for _, addr := range addrs {
		if ipv6 := addr.To4() == nil; ipv6 {
			fmt.Printf("%s is IPv6 ready. IPv6 Address: %s\n", hostname, addr)
			return true
		}
	}

	fmt.Printf("%s does not have IPv6 support.\n", hostname)
	return false
}

func formatSourceCode(path string) error {
	sh.RunV("isort", path)
	return sh.RunV("black", path)
}

func loadEnvironments() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}
}

func setDevStage() {
	currentUser, err := user.Current()
	if err != nil {
		log.Fatal("Failed to get user")
	}
	os.Setenv("DEPLOYMENT_STAGE", currentUser.Username)
	// os.Setenv("DEPLOYMENT_STAGE", "dev")
}

func usetDevStage() {
	os.Unsetenv("DEPLOYMENT_STAGE")
}

func setProdStage() {
	os.Setenv("DEPLOYMENT_STAGE", "prod")
}

func usetProdStage() {
	os.Unsetenv("DEPLOYMENT_STAGE")
}

func SendApiRequests() {
	loadEnvironments()
	endpoint := os.Getenv("API_ENDPOINT")
	fmt.Println("API_ENDPOINT: ", endpoint)
	uuid := getUUID()
	message := getMessage()
	requestCount := REQUST_COUNT

	var wg sync.WaitGroup

	for i := 0; i < requestCount; i++ {
		req := NewRequest(endpoint, message, uuid)
		fmt.Println("Processing request ", i)
		req.log()
		wg.Add(1)
		go processRequest(req, &wg)
	}
	wg.Wait()
}

type ApiRequest struct {
	endpoint string
	message  string
	uuid     string
}

func (api *ApiRequest) getBody() []byte {
	var body = map[string]string{
		"biography":    "you are an AI chatBot",
		"input_prompt": api.message,
	}
	result, err := json.Marshal(body)
	if err != nil {
		log.Fatal("unable to marshal body")
	}
	return result
}

func (api *ApiRequest) log() {
	fmt.Println(api.uuid, string(api.getBody()))
}

func NewRequest(endpoint, message, uuid string) *ApiRequest {
	return &ApiRequest{
		endpoint,
		message,
		uuid,
	}
}

func processRequest(request *ApiRequest, wg *sync.WaitGroup) {

	bodyReader := bytes.NewBuffer(request.getBody())
	req, err := http.NewRequest(http.MethodPost, request.endpoint, bodyReader)

	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("idempotency-key", request.uuid)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{
		Timeout: time.Second * 60,
	}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Failed to send request")
		fmt.Println(err)
	}
	defer resp.Body.Close()

	fmt.Println("response Status:", resp.Status)
	body, _ := io.ReadAll(resp.Body)
	fmt.Println("response Body:", string(body))
	wg.Done()
}

func getUUID() string {
	uuid := uuid.New()
	return uuid.String()
}

func getMessage() string {
	return "Tell me a funny german story"
}

func Cors() {
	// Replace with your API endpoint
	apiURL := "https://ecwgz0kvs1.execute-api.eu-north-1.amazonaws.com/prod/chat"

	// Replace with the actual payload you want to send
	payload := []byte(`{
		"biography": "large language model trained by OpenAI",
		"input_prompt": "give a car name"
	}`)

	// Create a new request with the POST method
	req, err := http.NewRequest("OPTIONS", apiURL, bytes.NewBuffer(payload))
	if err != nil {
		fmt.Println("Error creating request:", err)
		return
	}

	// Set the "Content-Type" header
	req.Header.Set("Content-Type", "application/json")

	// Set the custom "idempotency-key" header
	req.Header.Set("idempotency-key", getUUID())

	// Make the request
	client := http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Error making request:", err)
		return
	}
	defer resp.Body.Close()

	// Read the response body
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		fmt.Println("Error reading response body:", err)
		return
	}

	// Print the response status and body
	fmt.Println("Response Status:", resp.Status)
	fmt.Println("Response Body:", string(body))

	// Check for CORS headers
	allowedOrigin := resp.Header.Get("Access-Control-Allow-Origin")
	allowedMethods := resp.Header.Get("Access-Control-Allow-Methods")

	fmt.Println(allowedOrigin)
	fmt.Println(allowedMethods)

	if allowedOrigin != "" && allowedMethods != "" {
		fmt.Println("CORS is enabled. Allowed Origin:", allowedOrigin, "Allowed Methods:", allowedMethods)
	} else {
		fmt.Println("CORS is not enabled.")
	}
}
