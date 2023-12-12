//go:build mage

package main

import (
	"errors"
	"fmt"
	"net"

	"github.com/magefile/mage/sh"
)

// login to aws sso
func Login() error {
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

// deploy dev  stack to your default AWS
func DeployDev() error {
	return sh.RunV("cdk", "deploy", "--app", "python3 dev-app.py", "--require-approval=never")
}

// deploy this stack to your default AWS
func Deploy() error {
	return sh.RunV("cdk", "deploy")
}

// list all stacks in the app
func Ls() error {
	return sh.RunV("cdk", "ls")
}

// synth cdk (Do this only once)
func Synth() error {
	return sh.RunV("cdk", "synth")
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
	if err := formatSourceCode("src"); err != nil {
		return err
	}
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
	return sh.RunV("black", path)
}
