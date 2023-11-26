//go:build mage

package main

import (
	"errors"
	"fmt"
	"net"
)

// Check for ipv6
func CheckIp(hostname string) error {
	fmt.Println("Checking", hostname)
	if !isIPv6Ready(hostname) {
		return errors.New("IPv6 not ready")
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
